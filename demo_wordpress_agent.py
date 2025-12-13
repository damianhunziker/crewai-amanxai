#!/usr/bin/env python3
"""
Demo: Wie Agenten das direkte WordPress API Format verwenden können
"""

from crewai import Agent, Task, Crew
from core.universal_nango_api_tool import UniversalAPITool
from core.llm_streaming_client import StreamingLLM

def demo_wordpress_agent():
    """Demonstriert einen Agenten der WordPress API direkt verwendet"""

    print("🚀 WordPress Agent Demo")
    print("=" * 50)

    # LLM mit Streaming-Unterstützung
    llm = StreamingLLM(
        model_name="Qwen3-4B-Q5_K_M",
        base_url="http://localhost:5020/v1"
    )

    # Agent mit WordPress Tool
    wordpress_agent = Agent(
        role="WordPress Content Manager",
        goal="Verwalte WordPress-Inhalte über die REST API",
        backstory="Ich bin ein erfahrener Content-Manager mit direkten Zugriff auf WordPress APIs.",
        tools=[UniversalAPITool()],
        llm=llm,
        verbose=True
    )

    # Beispiel-Task: WordPress Posts abrufen
    task = Task(
        description="""
        Verwende die WordPress API um alle veröffentlichten Posts abzurufen.

        Verwende das universelle API Tool mit diesem exakten Format:
        {
          "provider": "wordpress",
          "endpoint": "/posts",
          "method": "GET",
          "params": {"status": "publish"}
        }

        Gib eine Zusammenfassung der Posts zurück.
        """,
        expected_output="Zusammenfassung der WordPress Posts mit Titel und Status",
        agent=wordpress_agent
    )

    # Crew ausführen
    crew = Crew(
        agents=[wordpress_agent],
        tasks=[task],
        verbose=True
    )

    print("🤖 Agent wird gestartet...")
    print("📝 Task: WordPress Posts abrufen")
    print("-" * 50)

    try:
        result = crew.kickoff()
        print("\n✅ Ergebnis:")
        print(result)
        return True
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        return False

if __name__ == "__main__":
    success = demo_wordpress_agent()
    if success:
        print("\n🎉 WordPress Agent Demo erfolgreich!")
    else:
        print("\n💥 WordPress Agent Demo fehlgeschlagen!")