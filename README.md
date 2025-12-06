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

4. Ensure a local OpenAI-compatible LLM server is running on `http://localhost:5020/v1` (as configured in `main.py`).

5. Run the script:
   ```bash
   python main.py
   ```

## Notes
- The `.env` file contains environment variables and is ignored by git.
- Adjust proxies and API settings in `main.py` or `.env` as needed.
