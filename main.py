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
from crewai import BaseLLM
from openai import OpenAI
from typing import Union

load_dotenv()

# Add current directory to path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

# Postfix to append to every user input
USER_INPUT_POSTFIX = os.getenv("USER_INPUT_POSTFIX", "")

# Custom LLM for local server (bypasses LiteLLM issues)
class LocalLLM(BaseLLM):
    def __init__(self, model: str = "Llama-3.2-3B-Instruct-Q4_K_M", temperature: Optional[float] = None):
        super().__init__(model=model, temperature=temperature)
        self.client = OpenAI(
            base_url="http://localhost:5020/v1",
            api_key="dummy"
        )

    def call(self, messages: Union[str, List[Dict[str, str]]],
             tools: Optional[List[dict]] = None,
             callbacks: Optional[List[Any]] = None,
             available_functions: Optional[Dict[str, Any]] = None,
             **kwargs) -> Union[str, Any]:

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature or 0.7
        }

        if tools and self.supports_function_calling():
            payload["tools"] = tools

        response = self.client.chat.completions.create(**payload)
        return response.choices[0].message.content

    def supports_function_calling(self) -> bool:
        return True

    def get_context_window_size(self) -> int:
        return 8192

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

# Custom LLM for local server
llm = LocalLLM()

os.environ.update({
    'NO_PROXY': 'localhost,127.0.0.1',
    'HTTP_PROXY': '',
    'HTTPS_PROXY': '',
    'OPENAI_API_BASE': 'http://localhost:5020/v1'
})

chatml_template = """<|im_start|>{role}
{content}<|im_end|>"""

# Custom LLM for local server
llm = LocalLLM()

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
                        result = f"Items: {[item['name'] for item in items]}"
                    else:
                        result = "No items found."
                except Exception as e:
                    result = f"Error listing items: {str(e)}"
                tool_logger.info(f"List items result: {result}")
                return result
            elif action == "get" and len(parts) > 2 and parts[1] == "item":
                item_id = parts[2]
                item = bw_client.get_item(item_id)
                result = f"Item: {item}" if item else "Item not found."
                tool_logger.info(f"Get item result: {result}")
                return result
            elif action == "search" and len(parts) > 2 and parts[1] == "items":
                term = " ".join(parts[2:])
                items = bw_client.search_items(term)
                result = f"Found {len(items)} items matching '{term}'"
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
    goal="Koordiniere alle Agenten und verwalte Kundenprojekte effizient.",
    backstory="Du bist der zentrale Manager der Vyftec Webagentur. Du koordinierst alle spezialisierten Agenten. Verwende Tools im korrekten Format: Action: tool_name\nAction Input: {\"param\": \"value\"}",
    tools=[AutonomousBitwardenCLITool()],  # Primary tool for passwords
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
    memory=True,
    verbose=True
)

# Function to check server health
def check_server_health():
    server_url = "http://localhost:5020"
    try:
        # Check models endpoint
        response = requests.get(f"{server_url}/v1/models", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server not healthy: {response.status_code}")
            return False
        models = response.json().get("data", [])
        print(f"✅ Server healthy. Available models: {[m['id'] for m in models]}")
        
        # Test embedding via proxy
        test_text = "Hello world"
        embed_response = requests.post(
            f"{server_url}/v1/embeddings",
            json={"input": test_text, "model": "bge-m3"},
            timeout=10
        )
        if embed_response.status_code == 200:
            data = embed_response.json()
            embedding = data["data"][0]["embedding"]
            print(f"✅ Embedding test successful. Dimension: {len(embedding)}")
            return True
        else:
            print(f"❌ Embedding test failed: {embed_response.status_code} - {embed_response.text}")
            return False
    except Exception as e:
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

# Chat function for manager
async def chat_with_manager(user_message: str, conversation_manager: ConversationManager) -> str:
    conversation_manager.add_turn("user", user_message)

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

    result = await temp_crew.kickoff_async()
    conversation_manager.add_turn("assistant", str(result))
    return str(result)

# Check server before running
if not check_server_health():
    print("Aborting due to server issues.")
    exit(1)

# Simple chat interface
async def main_chat_loop():
    conversation_manager = ConversationManager()
    print("🤖 Manager Chat Interface")
    print("Type 'quit' to exit")
    while True:
        user_input = input("\n👤 You: ").strip()
        if user_input.lower() in ['quit', 'exit']:
            break
        response = await chat_with_manager(user_input, conversation_manager)
        print(f"\n🤖 Manager: {response}")

if __name__ == "__main__":
    asyncio.run(main_chat_loop())

# Alternative: Run the fixed crew
# result = crew.kickoff()
# print(result)