# crewai-amanxai

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd crewai-amanxai
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables in `.env`:
   - `OPENAI_API_KEY`: For cloud LLM usage
   - `BITWARDEN_AGENT_EMAIL`: Bitwarden account email
   - `BITWARDEN_AGENT_PASSWORD`: Bitwarden master password

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

## Notes
- The `.env` file contains sensitive data and is ignored by git.
- Adjust server URLs and ports in `main.py` as needed.
- The system uses a chat interface for agent interaction.
