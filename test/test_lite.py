from crewai import LLM, Agent, Task, Crew
import os

local_llm = LLM(
    model="openai/Llama-3.2-3B-Instruct-Q4_K_M",
    api_key="empty",
    base_url="http://localhost:5020/v1"
)

agent = Agent(
    role="Tester",
    goal="Test LLM",
    backstory="Testing",
    llm=local_llm
)

task = Task(
    description="Say hello",
    expected_output="Hello message",
    agent=agent
)

crew = Crew(agents=[agent], tasks=[task])

try:
    result = crew.kickoff()
    print(f"Success: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()