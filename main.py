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

# Import Streaming Client
from core.llm_streaming_client import streaming_client, LlamaStreamingClient, AsyncLlamaStreamingClient

load_dotenv()

# Add current directory to path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

# Postfix to append to every user input
USER_INPUT_POSTFIX = os.getenv("USER_INPUT_POSTFIX", "")

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

local_llm = LLM(
    model="openai/Qwen3-4B-Q5_K_M",
    api_key="empty",
    base_url="http://localhost:5020/v1"
)

cloud_llm_deepseek_chat = LLM(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

gemini_llm = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.1,
)

cloud_llm_gpt4 = LLM(
    model="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY")
)

llm = local_llm

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

# Create agents
editor = Agent(
    role="Content Editor Specialist",
    goal="Erstelle hochwertige, plattformspezifische Inhalte für verschiedene Formate.",
    backstory="Du bist ein erfahrener Content-Editor mit Spezialisierung auf verschiedene Plattformen.",
    tools=[EditorTool()],
    llm=llm,  # Cloud for creativity
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
    goal="Koordiniere alle Agenten und verwalte Kundenprojekte effizient. Du kannst jetzt jede API verwenden, die über OpenAPI-Specs verfügbar ist, ohne dass spezifischer Code dafür geschrieben werden muss.",
    backstory="Du bist der zentrale Manager der Vyftec Webagentur mit Zugriff auf dynamische LLM-gesteuerte API-Tools. Du koordinierst alle spezialisierten Agenten und kannst universelle API-Integrationen nutzen.",
    tools=[AutonomousBitwardenCLITool()] + llm_api_tools,  # Combine existing and new LLM API tools
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
    allow_delegation=True,
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
    description="Koordiniere das Projekt und stelle sicher, dass alle Anforderungen erfüllt sind.",
    expected_output="Projektzusammenfassung mit nächsten Schritten.",
    agent=manager
)

crew = Crew(
    agents=[researcher, editor, manager],
    tasks=[research_task, editor_task, management_task],
    embedder=embedder,
    memory=False,
    verbose=True
)

# Function to check server health with streaming support
def check_server_health(verbose: bool = True):
    """Prüft Server-Health mit Streaming-Unterstützung"""
    server_url = "http://localhost:5020"
    
    # Check using streaming client first (more comprehensive)
    if verbose:
        print("🔍 Prüfe Server-Health mit Streaming-Client...")
    
    try:
        # Check using streaming client
        if streaming_client.check_server_health():
            if verbose:
                print("✅ Streaming-Client: Server ist erreichbar und gesund")
            
            # Check models endpoint
            response = requests.get(f"{server_url}/v1/models", timeout=5)
            if response.status_code != 200:
                if verbose:
                    print(f"❌ Models endpoint nicht erreichbar: {response.status_code}")
                return False
            
            models = response.json().get("data", [])
            if verbose:
                print(f"📊 Verfügbare Modelle: {[m['id'] for m in models]}")
            
            # Test streaming capability
            if verbose:
                print("🧪 Teste Streaming-Fähigkeit...")
            
            # Quick streaming test
            test_prompt = "Hello"
            try:
                test_stream = streaming_client.stream_completion(test_prompt, max_tokens=2)
                first_token = next(test_stream, None)
                if first_token:
                    if verbose:
                        print(f"✅ Streaming funktioniert: '{first_token}'")
                    return True
                else:
                    if verbose:
                        print("⚠️  Streaming test: Keine Tokens empfangen")
                    return True  # Server antwortet, aber kein Token
            except Exception as e:
                if verbose:
                    print(f"⚠️  Streaming test fehlgeschlagen (Server antwortet trotzdem): {e}")
                return True  # Server ist erreichbar, auch wenn Streaming fehlschlägt
            
            return True
        else:
            if verbose:
                print("❌ Streaming-Client: Server nicht erreichbar")
            return False
            
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

# Chat function for manager with optional streaming
async def chat_with_manager(user_message: str, conversation_manager: ConversationManager, use_streaming: bool = False) -> str:
    conversation_manager.add_turn("user", user_message)

    # Check if user wants streaming
    if "stream" in user_message.lower() or "live" in user_message.lower():
        use_streaming = True
    
    # Analyze message type
    message_lower = user_message.lower()
    research_keywords = ["recherche", "bericht", "analyse", "studie", "untersuchung", "informationen", "daten"]
    editor_keywords = ["content", "artikel", "schreiben", "text", "inhalt", "erstellen", "wordpress", "forum", "social"]
    management_keywords = ["projekt", "management", "koordination", "planung", "bitwarden", "passwort", "api"]

    if any(k in message_lower for k in research_keywords):
        # Research task
        task = Task(
            description=f"Research request: {user_message}\n\nContext: {conversation_manager.get_recent_context()}",
            expected_output="Comprehensive research report with findings and sources.",
            agent=researcher
        )
        temp_crew = Crew(agents=[researcher], tasks=[task], embedder=embedder, memory=False, verbose=True)
    elif any(k in message_lower for k in editor_keywords):
        # Editor task
        task = Task(
            description=f"Content creation: {user_message}\n\nContext: {conversation_manager.get_recent_context()}",
            expected_output="High-quality content for the requested format.",
            agent=editor
        )
        temp_crew = Crew(agents=[editor], tasks=[task], embedder=embedder, memory=False, verbose=True)
    else:
        # Management task
        task = Task(
            description=f"Management request: {user_message}\n\nContext: {conversation_manager.get_recent_context()}",
            expected_output="Strategic management response with recommendations.",
            agent=manager
        )
        temp_crew = Crew(agents=[manager], tasks=[task], embedder=embedder, memory=False, verbose=True)

    if use_streaming:
        # Use streaming for the response
        print("\n🎯 Streaming-Antwort aktiviert...")
        print("🤖 Manager: ", end='', flush=True)
        
        # Create a streaming response using the llama.cpp API directly
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ]
        
        full_response = ""
        try:
            for token in streaming_client.stream_chat(messages, max_tokens=500):
                print(token, end='', flush=True)
                full_response += token
            
            print()  # New line after streaming
            conversation_manager.add_turn("assistant", full_response)
            return full_response
            
        except Exception as e:
            print(f"\n⚠️  Streaming fehlgeschlagen, verwende normale Antwort: {e}")
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
    print("🤖 Manager Chat Interface mit Streaming-Unterstützung")
    print("Type 'quit' to exit")
    print("Type 'stream' or 'live' in your message for streaming response")
    print("Type 'test streaming' to test streaming functionality")
    print("-" * 50)
    
    while True:
        user_input = input("\n👤 You: ").strip()
        if user_input.lower() in ['quit', 'exit']:
            break
        
        # Special command: test streaming
        if user_input.lower() == 'test streaming':
            await test_streaming_demo()
            continue
        
        # Check if streaming should be used
        use_streaming = "stream" in user_input.lower() or "live" in user_input.lower()
        
        if use_streaming:
            print(f"🎯 Streaming aktiviert für diese Anfrage...")
        
        response = await chat_with_manager(user_input, conversation_manager, use_streaming=use_streaming)
        
        # Only print if not already streamed
        if not use_streaming:
            print(f"\n🤖 Manager: {response}")

# Streaming demo function
async def test_streaming_demo():
    """Demonstriert die Streaming-Funktionalität"""
    print("\n" + "=" * 60)
    print("🧪 Llama.cpp Streaming Demo")
    print("=" * 60)
    
    # Check server health
    if not check_server_health(verbose=False):
        print("❌ Server nicht erreichbar. Bitte starte llama-server.")
        print("   Startbefehl: ./scripts/start_llama_optimized.sh")
        return
    
    print("✅ Server ist erreichbar")
    
    # Demo 1: Chat Streaming
    print("\n1. Chat-Streaming Demo:")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ]
    
    print(f"Prompt: {messages[1]['content']}")
    print("Streaming response: ", end='', flush=True)
    
    full_response = ""
    try:
        for token in streaming_client.stream_chat(messages, max_tokens=100):
            print(token, end='', flush=True)
            full_response += token
        print(f"\n✅ Chat-Streaming erfolgreich ({len(full_response)} Zeichen)")
    except Exception as e:
        print(f"\n❌ Chat-Streaming fehlgeschlagen: {e}")
    
    # Demo 2: Completion Streaming
    print("\n2. Completion-Streaming Demo:")
    prompt = "The future of artificial intelligence will"
    
    print(f"Prompt: {prompt}")
    print("Streaming: ", end='', flush=True)
    
    try:
        for token in streaming_client.stream_completion(prompt, max_tokens=50):
            print(token, end='', flush=True)
        print("\n✅ Completion-Streaming erfolgreich")
    except Exception as e:
        print(f"\n❌ Completion-Streaming fehlgeschlagen: {e}")
    
    # Demo 3: Performance test
    print("\n3. Performance Test:")
    print("Messe Latenz bis zum ersten Token...")
    
    import time
    start_time = time.time()
    first_token_received = False
    
    try:
        for token in streaming_client.stream_completion("Hello", max_tokens=5):
            if not first_token_received:
                first_token_time = time.time() - start_time
                print(f"   Erstes Token nach: {first_token_time:.3f}s")
                first_token_received = True
                break
    except Exception as e:
        print(f"   ❌ Performance test fehlgeschlagen: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Streaming Demo abgeschlossen")
    print("=" * 60)
    print("\nTipp: Verwende 'stream' oder 'live' in deiner Nachricht für Streaming-Antworten")

if __name__ == "__main__":
    # Check server health before starting
    print("🔍 Starte CrewAI mit Streaming-Unterstützung...")
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
