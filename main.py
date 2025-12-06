from crewai import LLM
from dotenv import load_dotenv
import os
import requests

load_dotenv()

os.environ.update({
    'NO_PROXY': 'localhost,127.0.0.1',
    'HTTP_PROXY': '',
    'HTTPS_PROXY': '',
    'OPENAI_API_BASE': 'http://localhost:5020/v1'
})

local_llm = LLM(
    model="openai/Llama-3.2-3B-Instruct-Q4_K_M",
    api_key="dummy",
    base_url="http://localhost:5020/v1"
)

cloud_llm = LLM(
    model="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY")
)

embedder = {
    "provider": "openai",
    "config": {
        "model": "bge-m3",
        "api_key": "dummy",
        "base_url": "http://localhost:5020/v1",
        "model_name": "bge-m3"
    }
}

from crewai import Agent

researcher = Agent(
    role='Market Research Analyst',
    goal='Analyze competitors and summarize their marketing strategies',
    backstory='An expert in market intelligence and competitive analysis.',
    llm=local_llm,  # Uses local LLM
    allow_delegation=False
)

writer = Agent(
    role='Content Strategist',
    goal='Use research to create a compelling marketing strategy document',
    backstory='A seasoned content strategist with a flair for storytelling.',
    llm=local_llm  # Uses cloud LLM
)

from crewai import Task

task1 = Task(
    description="List top 3 competitors and their marketing strategies based on current trends.",
    agent=researcher,
    expected_output="A summary of 3 competitors with key marketing strategies."
)

task2 = Task(
    description="Create a content marketing strategy based on the competitor summary.",
    agent=writer,
    expected_output="A structured document with our content strategy inspired by competitors.",
    depends_on=[task1]
)

from crewai import Crew

crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
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

# Check server before running crew
if not check_server_health():
    print("Aborting due to server issues.")
    exit(1)

result = crew.kickoff()
print(result)