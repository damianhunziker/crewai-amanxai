# crewai-amanxai

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd crewai-amanxai
   ```

2. Create a virtual environment:
   ```bash
   /usr/local/opt/python@3.12/bin/python3.12 -m venv venv312
   source venv312/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables in `.env`:
   - `OPENAI_API_KEY`: For cloud LLM usage
   - `DEEPSEEK_API_KEY`: For DeepSeek LLM usage
   - `GEMINI_API_KEY`: For Gemini LLM usage
   - `BITWARDEN_AGENT_EMAIL`: Bitwarden account email
   - `BITWARDEN_AGENT_PASSWORD`: Bitwarden master password
   - `BRAVE_API_KEY`: For Brave Search MCP server
   - `USER_INPUT_POSTFIX`: Optional postfix to append to every user message at LLM call level (e.g., for system instructions). Applied globally via LLM hooks. Example: `USER_INPUT_POSTFIX="Always respond in German."`

5. Test Bitwarden integration:
   ```bash
   python test_bitwarden.py
   ```

6. Ensure servers are running:
   - Local LLM server on `http://localhost:5020/v1`
   - Embedding server on `http://localhost:8001/v1`

7. Run the chat interface:
   ```bash
   python main.py
   ```

## MCP Integration

This project integrates Model Context Protocol (MCP) servers as tools for CrewAI agents:

- **Brave Search MCP**: Web and local search capabilities
- **URL Reader MCP**: URL content reading and markdown processing
- **Perplexity MCP**: Advanced research and reasoning tools

The MCP servers are automatically connected via stdio transport and available to agents through the `mcps` field in agent configurations.

### MCP Server Requirements

Ensure the following MCP servers are available in your workspace:
- `/Users/jgtcdghun/workspace/brave_search/index.js` (requires BRAVE_API_KEY)
- `/Users/jgtcdghun/workspace/researcher-poster/mcp-servers/url-reader/server.py`
- `/Users/jgtcdghun/workspace/perplexity-mcp/perplexity-mcp-server/dist/index.js`

## Notes
- The `.env` file contains sensitive data and is ignored by git.
- Adjust server URLs and ports in `main.py` as needed.
- The system uses a chat interface for agent interaction.
- MCP tools enhance agent capabilities for research and data retrieval.
- `USER_INPUT_POSTFIX` allows appending custom text to every user message for additional context or instructions.
