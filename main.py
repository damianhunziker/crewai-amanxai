from crewai import LLM
import os

os.environ.update({
    'NO_PROXY': 'localhost,127.0.0.1',
    'HTTP_PROXY': '',
    'HTTPS_PROXY': '',
    'OPENAI_API_BASE': 'http://localhost:5020/v1'
})

llm = LLM(
    model="openai/Llama-3.2-3B-Instruct-Q4_K_M",
    api_key="dummy"
)

from crewai import Agent

researcher = Agent(
    role='Market Research Analyst',
    goal='Analyze competitors and summarize their marketing strategies',
    backstory='An expert in market intelligence and competitive analysis.',
    llm=llm,
    allow_delegation=False
)

writer = Agent(
    role='Content Strategist',
    goal='Use research to create a compelling marketing strategy document',
    backstory='A seasoned content strategist with a flair for storytelling.',
    llm=llm
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
    verbose=True
)

result = crew.kickoff()
print(result)