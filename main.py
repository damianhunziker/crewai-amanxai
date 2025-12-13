from crewai import LLM, Agent, Task, Crew
from dotenv import load_dotenv
import os
import requests
import subprocess
import logging
import sys
import json
import asyncio
from typing import Any, Dict, List, Optional, Type
from crewai.tools import BaseTool
from pydantic import BaseModel
from crewai.mcp import MCPServerStdio
from crewai.hooks import register_before_llm_call_hook, LLMCallHookContext
from crewai.utilities.streaming import crewai_event_bus

# Import Streaming Event Listener
from core.streaming_event_listener import streaming_event_listener, print_streaming_tokens, collect_streaming_response

# Suppress litellm debug info
try:
    import litellm
    litellm.suppress_debug_info = True
    # Also disable litellm logging
    os.environ['LITELLM_LOG'] = ''
except ImportError:
    pass

load_dotenv()

# Add current directory to path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

# Postfix to append to every user input
USER_INPUT_POSTFIX = os.getenv("USER_INPUT_POSTFIX", "")

# Streaming configuration - enabled by default, can be disabled via env var
DISABLE_STREAMING = os.getenv("DISABLE_STREAMING", "").lower() in ("true", "1", "yes", "on")
STREAMING_ENABLED_BY_DEFAULT = not DISABLE_STREAMING

# LLM Hook to append postfix to user messages at LLM call level
def append_user_postfix(context: LLMCallHookContext) -> None:
    if USER_INPUT_POSTFIX:
        # Find the last user message and append postfix
        for msg in reversed(context.messages):
            if msg.get("role") == "user":
                msg["content"] = f"{msg['content']} {USER_INPUT_POSTFIX}"
                break
    return None

# Register the global hook
register_before_llm_call_hook(append_user_postfix)

os.environ.update({
    'NO_PROXY': 'localhost,127.0.0.1',
    'HTTP_PROXY': '',
    'HTTPS_PROXY': '',
    'OPENAI_API_BASE': 'http://localhost:5020/v1',
    'NANGO_SECRET_KEY': os.getenv('NANGO_SECRET_KEY', 'dummy-key-change-in-production')
})

chatml_template = """<|im_start|>{role}
{content}<|im_end|>"""

# LLM Configuration with streaming support
local_llm = LLM(
    #model="openai/Qwen3-4B-Q5_K_M",
    model="openai/Llama-3.2-3B-Instruct-Q4_K_M",
   
    api_key="empty",
    base_url="http://localhost:5020/v1",
    stream=True  # Use streaming by default
)

# Cloud LLMs (optional - comment out if not needed)
cloud_llm_deepseek_chat = None
if os.getenv("DEEPSEEK_API_KEY"):
    cloud_llm_deepseek_chat = LLM(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
        stream=True  # Enable streaming for cloud LLMs too
    )

cloud_llm_gpt4 = None
if os.getenv("OPENAI_API_KEY"):
    cloud_llm_gpt4 = LLM(
        model="gpt-4",
        api_key=os.getenv("OPENAI_API_KEY"),
        stream=True
    )

llm = cloud_llm_deepseek_chat  # Use local LLM by default

embedder = {
    "provider": "openai",
    "config": {
        "model": "bge-m3",
        "api_key": "dummy",
        "base_url": "http://localhost:8001/v1",
        "model_name": "bge-m3"
    }
}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tool logging to file
tool_logger = logging.getLogger('bitwarden_tool')
tool_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('logs/bitwarden_tool.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
tool_logger.addHandler(file_handler)

# Tool Schemas
class EditorToolSchema(BaseModel):
    query: Any

class AutonomousBitwardenCLISchema(BaseModel):
    command: str
    description: Optional[str] = None

# Editor Tool (adapted from vyftec-crew)
class EditorTool(BaseTool):
    name: str = "editor"
    description: str = "Erstellt hochwertige Inhalte mit Template-Unterstützung."
    args_schema: Type[BaseModel] = EditorToolSchema

    async def _run(self, query: Any) -> str:
        # Forward to researcher-poster agent
        researcher_path = "/Users/jgtcdghun/workspace/researcher-poster/agent"
        if not os.path.exists(researcher_path):
            return "Researcher-Poster nicht verfügbar."

        try:
            cmd_str = " ".join([
                "cd", researcher_path, "&&",
                "/usr/local/opt/python@3.13/bin/python3.13", "cli.py",
                "research", f'"{str(query)}"',
                "--mode=auto", "--md-tools", "--max-duration", "20", "--json"
            ])
            process = await asyncio.subprocess.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600
            )
            if process.returncode == 0:
                return stdout.decode() or "Inhalt erfolgreich erstellt."
            else:
                return f"Fehler: {stderr.decode()}"
        except Exception as e:
            return f"Fehler: {str(e)}"

# Import the proper Bitwarden integration
from core.bitwarden_session_manager import initialize_bitwarden_session
from core.bitwarden_cli_integration import BitwardenCLIIntegration

# Import LLM API Integration
from core.llm_api_manager import DynamicAPIManager

# Import Fragment-Based API Tool
from core.fragment_based_api_tool import get_fragment_based_api_tool

# Auto-Setup Bitwarden Session bei Bedarf
try:
    from core.bitwarden_session_manager import initialize_bitwarden_session
    if not initialize_bitwarden_session():
        print("⚠️ Bitwarden Session nicht verfügbar - einige Features eingeschränkt")
        print("💡 Führe aus: python scripts/setup_bitwarden_session.py")
except Exception as e:
    print(f"⚠️ Bitwarden Auto-Setup fehlgeschlagen: {e}")

# Autonomous Bitwarden CLI Tool (using proper integration)
class AutonomousBitwardenCLITool(BaseTool):
    name: str = "autonomous_bitwarden_cli"
    description: str = "Führt Bitwarden-CLI-Befehle aus. WICHTIG: Vault muss entsperrt sein, bevor Items gelesen werden können. Unterstützt: status, unlock, list items, get item <id>, search items <term>, create item, etc."
    args_schema: Type[BaseModel] = AutonomousBitwardenCLISchema

    def __init__(self):
        super().__init__()

    def _run(self, command: str, description: Optional[str] = None) -> str:
        tool_logger.info(f"Tool called with command: {command}, description: {description}")
        try:
            # Initialize Bitwarden session and client
            initialize_bitwarden_session()
            bw_client = BitwardenCLIIntegration()

            # Parse command
            parts = command.split()
            if not parts:
                result = "No command provided."
                tool_logger.info(f"Result: {result}")
                return result

            action = parts[0]

            if action == "status":
                status = bw_client.get_status()
                result = f"Status: {status}"
                tool_logger.info(f"Status result: {result}")
                return result
            elif action == "unlock":
                if bw_client.unlock():
                    result = "Vault unlocked successfully."
                else:
                    result = "Failed to unlock vault."
                tool_logger.info(f"Unlock result: {result}")
                return result
            elif action == "list" and len(parts) > 1 and parts[1] == "items":
                if not bw_client.session_key:
                    tool_logger.info("Session not available, attempting unlock")
                    bw_client.unlock()
                try:
                    stdout, stderr = bw_client._run_bw_command(["list", "items"])
                    tool_logger.info(f"CLI command: bw list items")
                    tool_logger.info(f"CLI stdout: {stdout}")
                    tool_logger.info(f"CLI stderr: {stderr}")
                    if stdout:
                        items = json.loads(stdout)
                        # Include both name and ID in the result
                        item_list = [f"{item.get('name', 'Unknown')} (ID: {item.get('id', 'N/A')})" for item in items]
                        result = f"Items: {item_list}"
                    else:
                        result = "No items found."
                except Exception as e:
                    result = f"Error listing items: {str(e)}"
                tool_logger.info(f"List items result: {result}")
                return result
            elif action == "get" and len(parts) > 2 and parts[1] == "item":
                item_id = parts[2]
                item = bw_client.get_item(item_id)
                if item:
                    item_name = item.get('name', 'Unknown')
                    result = f"Item (ID: {item_id}): {item_name} - {item}"
                else:
                    result = f"Item with ID {item_id} not found."
                tool_logger.info(f"Get item result: {result}")
                return result
            elif action == "search" and len(parts) > 2 and parts[1] == "items":
                term = " ".join(parts[2:])
                items = bw_client.search_items(term)
                if items:
                    item_list = [f"{item.get('name', 'Unknown')} (ID: {item.get('id', 'N/A')})" for item in items]
                    result = f"Found {len(items)} items matching '{term}': {item_list}"
                else:
                    result = f"No items found matching '{term}'"
                tool_logger.info(f"Search result: {result}")
                return result
            else:
                result = f"Unsupported command: {command}. Supported: status, unlock, list items, get item <id>, search items <term>"
                tool_logger.info(f"Result: {result}")
                return result
        except Exception as e:
            result = f"Error: {str(e)}"
            tool_logger.error(f"Exception: {str(e)}")
            return result

# Initialize LLM API Manager
dynamic_api_manager = DynamicAPIManager()
llm_api_tools = dynamic_api_manager.get_tools_for_agent("manager")

# Initialize Fragment-Based API Tool
fragment_api_tool = get_fragment_based_api_tool()

# Create agents
editor = Agent(
    role="Content Editor Specialist",
    goal="Erstelle hochwertige, plattformspezifische Inhalte für verschiedene Formate.",
    backstory="Du bist ein erfahrener Content-Editor mit Spezialisierung auf verschiedene Plattformen.",
    tools=[AutonomousBitwardenCLITool()] + llm_api_tools + [fragment_api_tool],
    llm=llm,
    verbose=True,
    allow_delegation=True,
    memory=False
)

researcher = Agent(
    role="Senior Research Analyst",
    goal="Führe umfassende Recherchen durch und erstelle detaillierte Berichte.",
    backstory="Du bist ein hochqualifizierter Research Analyst mit Zugang zu fortschrittlichen Tools.",
    tools=[EditorTool()],  # Forwards to researcher-poster
    mcps=[
        MCPServerStdio(
            command="/Users/jgtcdghun/.nvm/versions/node/v20.19.2/bin/node",
            args=["/Users/jgtcdghun/workspace/brave_search/index.js"]
        ),
        MCPServerStdio(
            command="/usr/local/bin/python3",
            args=["/Users/jgtcdghun/workspace/researcher-poster/mcp-servers/url-reader/server.py"]
        ),
        MCPServerStdio(
            command="/Users/jgtcdghun/.nvm/versions/node/v20.19.2/bin/node",
            args=["/Users/jgtcdghun/workspace/perplexity-mcp/perplexity-mcp-server/dist/index.js"]
        )
    ],
    llm=llm,
    verbose=True,
    allow_delegation=False,
    memory=False
)

manager = Agent(
    role="Vyftec Manager",
    goal="Antworte kurz und prägnant auf User-Anfragen. Beantworte nur die gestellte Frage, erfinde nichts hinzu und schmücke nicht aus. Verwende Tools wenn nötig, aber halte Antworten auf das Wesentliche beschränkt.",
    backstory="Du bist ein effizienter Manager der Vyftec Webagentur. Du antwortest direkt und präzise, ohne unnötige Ausschmückungen. Du nutzt Tools nur wenn notwendig und gibst klare, kurze Antworten.",
    tools=[AutonomousBitwardenCLITool()] + llm_api_tools + [fragment_api_tool],  # Combine existing and new LLM API tools
    mcps=[
        MCPServerStdio(
            command="/Users/jgtcdghun/.nvm/versions/node/v20.19.2/bin/node",
            args=["/Users/jgtcdghun/workspace/brave_search/index.js"]
        ),
        MCPServerStdio(
            command="/usr/local/bin/python3",
            args=["/Users/jgtcdghun/workspace/researcher-poster/mcp-servers/url-reader/server.py"]
        ),
        MCPServerStdio(
            command="/Users/jgtcdghun/.nvm/versions/node/v20.19.2/bin/node",
            args=["/Users/jgtcdghun/workspace/perplexity-mcp/perplexity-mcp-server/dist/index.js"]
        )
    ],
    llm=llm,
    verbose=True,
    allow_delegation=False,
    memory=False
)

# Create tasks
research_task = Task(
    description="Führe eine umfassende Recherche zu einem Thema durch.",
    expected_output="Detaillierter Forschungsbericht mit Quellen und Empfehlungen.",
    agent=researcher
)

editor_task = Task(
    description="Erstelle hochwertigen Content basierend auf der Recherche.",
    expected_output="Professioneller Content für die gewünschte Plattform.",
    agent=editor,
    depends_on=[research_task]
)

management_task = Task(
    description="Antworte kurz und prägnant auf die User-Anfrage. Beantworte nur die gestellte Frage, erfinde nichts hinzu und schmücke nicht aus. Verwende Tools wenn nötig, aber halte Antworten auf das Wesentliche beschränkt. Maximal 3-5 Sätze.",
    expected_output="Kurze, präzise Antwort auf die User-Anfrage.",
    agent=manager
)

crew = Crew(
    agents=[researcher, editor, manager],
    tasks=[research_task, editor_task, management_task],
    embedder=embedder,
    memory=False,
    verbose=True
)

# Function to check server health
def check_server_health(verbose: bool = True):
    """Prüft Server-Health"""
    server_url = "http://localhost:5020"
    
    if verbose:
        print("🔍 Prüfe Server-Health...")
    
    try:
        # Check health endpoint
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code != 200:
            if verbose:
                print(f"❌ Health endpoint nicht erreichbar: {response.status_code}")
            return False
        
        if verbose:
            print("✅ Server ist erreichbar")
        
        # Check models endpoint
        response = requests.get(f"{server_url}/v1/models", timeout=5)
        if response.status_code != 200:
            if verbose:
                print(f"❌ Models endpoint nicht erreichbar: {response.status_code}")
            return False
        
        models = response.json().get("data", [])
        if verbose:
            print(f"📊 Verfügbare Modelle: {[m['id'] for m in models]}")
        
        return True
            
    except Exception as e:
        if verbose:
            print(f"❌ Server check failed: {e}")
        return False

# Conversation manager for chat
class ConversationManager:
    def __init__(self, max_history_length: int = 20):
        self.conversation_history: List[Dict] = []
        self.max_history_length = max_history_length

    def add_turn(self, role: str, content: str):
        turn = {
            "role": role,
            "content": content,
            "timestamp": os.times()
        }
        self.conversation_history.append(turn)
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history.pop(0)

    def get_recent_context(self, turns: int = 5) -> str:
        recent = self.conversation_history[-turns:]
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent])

# Chat function for manager with streaming support
async def chat_with_manager(user_message: str, conversation_manager: ConversationManager, use_streaming: bool = STREAMING_ENABLED_BY_DEFAULT) -> str:
    conversation_manager.add_turn("user", user_message)

    # Check if user wants to disable streaming (default is enabled)
    if "no stream" in user_message.lower() or "disable stream" in user_message.lower():
        use_streaming = False
    elif "force stream" in user_message.lower() or "enable stream" in user_message.lower():
        use_streaming = True  # Explicitly enable even if disabled by env var
    
    # Analyze message type
    message_lower = user_message.lower()
    research_keywords = ["recherche", "bericht", "analyse", "studie", "untersuchung", "informationen", "daten"]
    editor_keywords = ["content", "artikel", "schreiben", "text", "inhalt", "erstellen", "wordpress", "forum", "social"]
    management_keywords = ["projekt", "management", "koordination", "planung", "bitwarden", "passwort", "api"]

    # Temporarily set agent verbose to False to reduce debug output
    original_researcher_verbose = researcher.verbose
    original_editor_verbose = editor.verbose
    original_manager_verbose = manager.verbose
    researcher.verbose = False
    editor.verbose = False
    manager.verbose = False
    
    # Temporarily disable MCP servers to prevent debug output
    original_researcher_mcps = researcher.mcps
    original_editor_mcps = editor.mcps
    original_manager_mcps = manager.mcps
    researcher.mcps = []
    editor.mcps = []
    manager.mcps = []
    
    try:
        if any(k in message_lower for k in research_keywords):
            # Research task
            task = Task(
                description=f"Research request: {user_message}\n\nContext: {conversation_manager.get_recent_context()}",
                expected_output="Comprehensive research report with findings and sources.",
                agent=researcher
            )
            temp_crew = Crew(agents=[researcher], tasks=[task], embedder=embedder, memory=False, verbose=False)
        elif any(k in message_lower for k in editor_keywords):
            # Editor task
            task = Task(
                description=f"Content creation: {user_message}\n\nContext: {conversation_manager.get_recent_context()}",
                expected_output="High-quality content for the requested format.",
                agent=editor
            )
            temp_crew = Crew(agents=[editor], tasks=[task], embedder=embedder, memory=False, verbose=False)
        else:
            # Management task - kurze, prägnante Antwort
            task = Task(
                description=f"Antworte kurz und prägnant auf: {user_message}\n\nRegeln:\n1. Beantworte nur die gestellte Frage\n2. Erfinde nichts hinzu\n3. Schmücke nicht aus\n4. Maximal 3-5 Sätze\n5. Verwende Tools nur wenn nötig\n\nContext: {conversation_manager.get_recent_context()}",
                expected_output="Kurze, präzise Antwort auf die User-Anfrage.",
                agent=manager
            )
            temp_crew = Crew(agents=[manager], tasks=[task], embedder=embedder, memory=False, verbose=False)
    finally:
        # Restore original verbose settings
        researcher.verbose = original_researcher_verbose
        editor.verbose = original_editor_verbose
        manager.verbose = original_manager_verbose
        # Restore original MCP settings
        researcher.mcps = original_researcher_mcps
        editor.mcps = original_editor_mcps
        manager.mcps = original_manager_mcps

    if use_streaming:
        # Use streaming for the response
        print("\n🎯 Streaming-Antwort aktiviert...")
        print("🤖 Manager: ", end='', flush=True)
        
        # Start the streaming event listener consumer
        collected_tokens = []
        
        def token_callback(token):
            print(token, end='', flush=True)
            collected_tokens.append(token)
        
        streaming_event_listener.start_consumer(callback=token_callback)
        
        # Execute the task
        try:
            result = await temp_crew.kickoff_async()
            
            # Wait for tokens to be processed
            import time
            timeout = 30  # 30 seconds timeout
            start_time = time.time()
            
            while streaming_event_listener._consumer_thread and streaming_event_listener._consumer_thread.is_alive():
                if time.time() - start_time > timeout:
                    break
                await asyncio.sleep(0.1)
            
            # Stop the consumer
            streaming_event_listener.stop_consumer()
            
            print()  # New line after streaming
            
            # Use collected tokens if available, otherwise use result
            if collected_tokens:
                full_response = ''.join(collected_tokens)
            else:
                full_response = str(result)
                
            conversation_manager.add_turn("assistant", full_response)
            return full_response
            
        except Exception as e:
            print(f"\n⚠️  Streaming fehlgeschlagen, verwende normale Antwort: {e}")
            streaming_event_listener.stop_consumer()
            # Fallback to normal crew response
            result = await temp_crew.kickoff_async()
            conversation_manager.add_turn("assistant", str(result))
            return str(result)
    else:
        # Normal crew response
        result = await temp_crew.kickoff_async()
        conversation_manager.add_turn("assistant", str(result))
        return str(result)

# Check server before running
if not check_server_health():
    print("Aborting due to server issues.")
    exit(1)

# Simple chat interface with streaming support
async def main_chat_loop():
    # Auto-unlock Bitwarden vault at chat start
    print("🔐 Attempting to unlock Bitwarden vault...")
    try:
        from core.bitwarden_cli_integration import BitwardenCLIIntegration
        bw_client = BitwardenCLIIntegration()
        if bw_client.unlock():
            print("✅ Bitwarden vault unlocked successfully")
        else:
            print("⚠️ Could not unlock Bitwarden vault - some features may be limited")
    except Exception as e:
        print(f"⚠️ Bitwarden unlock failed: {e} - continuing without Bitwarden features")

    conversation_manager = ConversationManager()
    streaming_status = "AKTIVIERT" if STREAMING_ENABLED_BY_DEFAULT else "DEAKTIVIERT"
    print(f"🤖 Manager Chat Interface (Streaming: {streaming_status})")
    print("Type 'quit' to exit")
    print("Type 'no stream' in your message to disable streaming for that response")
    print("Type 'test streaming' to test streaming functionality")
    if DISABLE_STREAMING:
        print("💡 Streaming wurde via DISABLE_STREAMING env var deaktiviert")
    print("-" * 50)
    
    while True:
        user_input = input("\n👤 You: ").strip()
        if user_input.lower() in ['quit', 'exit']:
            break
        
        # Special command: test streaming
        if user_input.lower() == 'test streaming':
            await test_streaming_demo()
            continue
        
        # Check if streaming should be disabled for this request
        force_disable_streaming = "no stream" in user_input.lower() or "disable stream" in user_input.lower()
        force_enable_streaming = "force stream" in user_input.lower() or "enable stream" in user_input.lower()

        # Use streaming by default unless explicitly disabled or forced
        use_streaming = STREAMING_ENABLED_BY_DEFAULT
        if force_disable_streaming:
            use_streaming = False
        elif force_enable_streaming:
            use_streaming = True

        if use_streaming:
            print(f"🎯 Streaming aktiviert für diese Anfrage...")
        elif force_disable_streaming:
            print(f"📝 Streaming deaktiviert für diese Anfrage...")
        
        response = await chat_with_manager(user_input, conversation_manager, use_streaming=use_streaming)
        
        # Only print if not already streamed
        if not use_streaming:
            print(f"\n🤖 Manager: {response}")

# Streaming demo function
async def test_streaming_demo():
    """Demonstriert die Streaming-Funktionalität"""
    print("\n" + "=" * 60)
    print("🧪 CrewAI Streaming Demo")
    print("=" * 60)
    
    # Check server health
    if not check_server_health(verbose=False):
        print("❌ Server nicht erreichbar. Bitte starte llama-server.")
        print("   Startbefehl: ./scripts/start_llama_optimized.sh")
        return
    
    print("✅ Server ist erreichbar")
    
    # Demo: Simple streaming test using LLM directly
    print("\n1. Direct LLM Streaming Demo:")
    print("Prompt: 'Explain quantum computing in simple terms.'")
    print("Streaming response: ", end='', flush=True)
    
    # Create a simple task with streaming
    test_task = Task(
        description="Explain quantum computing in simple terms.",
        expected_output="Simple explanation of quantum computing.",
        agent=manager
    )
    
    test_crew = Crew(agents=[manager], tasks=[test_task], embedder=embedder, memory=False, verbose=False)
    
    try:
        # Start streaming consumer
        collected_tokens = []
        
        def token_callback(token):
            print(token, end='', flush=True)
            collected_tokens.append(token)
        
        streaming_event_listener.start_consumer(callback=token_callback)
        
        # Execute with timeout
        import asyncio
        import time
        
        async def execute_with_timeout():
            return await test_crew.kickoff_async()
        
        try:
            result = await asyncio.wait_for(execute_with_timeout(), timeout=30)
            
            # Wait for tokens
            timeout = 10
            start_time = time.time()
            while streaming_event_listener._consumer_thread and streaming_event_listener._consumer_thread.is_alive():
                if time.time() - start_time > timeout:
                    break
                await asyncio.sleep(0.1)
            
            streaming_event_listener.stop_consumer()
            
            if collected_tokens:
                print(f"\n✅ Streaming erfolgreich ({len(collected_tokens)} Tokens)")
            else:
                print(f"\n⚠️  Keine Tokens empfangen, aber Antwort erhalten: {result[:100]}...")
                
        except asyncio.TimeoutError:
            print("\n⚠️  Timeout bei Streaming-Demo")
            streaming_event_listener.stop_consumer()
            
    except Exception as e:
        print(f"\n❌ Streaming fehlgeschlagen: {e}")
        streaming_event_listener.stop_consumer()
    
    print("\n" + "=" * 60)
    print("🎉 Streaming Demo abgeschlossen")
    print("=" * 60)
    print("\nTipp: Verwende 'stream' oder 'live' in deiner Nachricht für Streaming-Antworten")

if __name__ == "__main__":
    # Check server health before starting
    streaming_status = "AKTIVIERT" if STREAMING_ENABLED_BY_DEFAULT else "DEAKTIVIERT"
    print(f"🔍 Starte CrewAI (Streaming: {streaming_status})...")

    if DISABLE_STREAMING:
        print("💡 Streaming wurde via DISABLE_STREAMING env var deaktiviert")
        print("   Setze DISABLE_STREAMING=false um Streaming zu aktivieren")

    if not check_server_health():
        print("⚠️  Server-Probleme erkannt. Einige Features möglicherweise eingeschränkt.")
        print("   Starte Server mit: ./scripts/start_llama_optimized.sh")
        print("   Trotzdem fortfahren? (y/n): ", end='')
        response = input().strip().lower()
        if response != 'y':
            print("Abgebrochen.")
            exit(1)

    asyncio.run(main_chat_loop())

# Alternative: Run the fixed crew
# result = crew.kickoff()
# print(result)
