#!/usr/bin/env python3
"""
Test: Universelles Nango API Tool für Agenten

Demonstriert, wie Agenten mit einem einzigen Tool jede API über Nango ansprechen können.
"""

import os
import sys

# Pfad hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.universal_nango_api_tool import get_universal_api_tool

def test_universal_tool():
    """Teste das universelle Nango Tool"""
    print("🚀 UNIVERSAL NANGO API TOOL TEST")
    print("=" * 50)

    tool = get_universal_api_tool()

    # Tool-Info anzeigen
    print(f"🔧 Tool Name: {tool.name}")
    print(f"📝 Description: {tool.description}")
    print(f"📋 Args Schema: {tool.args_schema.__name__}")
    print(f"🎯 Agenten verwenden: {tool.name}(provider='github', endpoint='/user/repos', method='GET')")
    print()

    # Unterstützte Provider
    providers = tool.get_supported_providers()
    print(f"🌐 Unterstützte Provider ({len(providers)}):")
    for i, provider in enumerate(providers, 1):
        info = tool.get_provider_info(provider)
        print(f"  {i:2d}. {provider:<15} - {info['description'][:50]}...")
    print()

    # Beispielhafte API-Calls (ohne echte Ausführung)
    print("📡 BEISPIELHAFTE API-CALLS:")
    print("-" * 30)

    examples = [
        {
            "description": "GitHub: Aktuelle Repositories abrufen",
            "call": {
                "provider": "github",
                "endpoint": "/user/repos",
                "method": "GET",
                "description": "Liste meiner GitHub Repositories"
            }
        },
        {
            "description": "Notion: Datenbanken auflisten",
            "call": {
                "provider": "notion",
                "endpoint": "/databases",
                "method": "GET",
                "description": "Verfügbare Notion Datenbanken"
            }
        },
        {
            "description": "Slack: Nachricht senden",
            "call": {
                "provider": "slack",
                "endpoint": "/chat.postMessage",
                "method": "POST",
                "params": {"channel": "#general", "text": "Hello from CrewAI!"},
                "description": "Nachricht in Slack-Channel posten"
            }
        },
        {
            "description": "OpenAI: Modelle auflisten",
            "call": {
                "provider": "openai",
                "endpoint": "/models",
                "method": "GET",
                "description": "Verfügbare OpenAI Modelle"
            }
        }
    ]

    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['description']}")
        print(f"   Tool-Call: {tool.name}(")
        for key, value in example['call'].items():
            if key == 'params':
                print(f"      {key}={value},")
            else:
                print(f"      {key}='{value}',")
        print("   )")
        print()

    # Häufige Endpoints für jeden Provider
    print("🔗 HÄUFIGE ENDPOINTS PRO PROVIDER:")
    print("-" * 40)

    for provider in ['github', 'notion', 'slack', 'openai']:
        print(f"\n{provider.upper()}:")
        endpoints = tool.list_common_endpoints(provider)
        for endpoint in endpoints[:3]:  # Zeige nur erste 3
            print(f"  {endpoint['method']} {endpoint['endpoint']}")
            print(f"    → {endpoint['description']}")

    print("\n" + "=" * 50)
    print("🎉 EIN TOOL FÜR ALLE APIs!")
    print("   Agenten müssen nur provider + endpoint + method angeben!")
    print("   Nango übernimmt Auth, Routing und alles andere automatisch!")

def simulate_agent_workflow():
    """Simuliert einen Agenten-Workflow mit dem universellen Tool"""
    print("\n🤖 SIMULIERTER AGENTEN-WORKFLOW:")
    print("-" * 40)

    workflow = [
        "Agent erhält Aufgabe: 'Aktualisiere GitHub Issue #123'",
        "Agent denkt: 'Ich brauche GitHub API'",
        "Agent ruft Tool auf: universal_nango_api(provider='github', endpoint='/repos/owner/repo/issues/123', method='PATCH', params={'title': 'Updated Title'})",
        "Nango empfängt Call und identifiziert Provider 'github'",
        "Nango holt gespeicherte Connection für github (8c88a265-f4ac-4c7b-96a6-d8526ac8eeaa)",
        "Nango injiziert Auth-Token automatisch",
        "Call geht an: https://api.github.com/repos/owner/repo/issues/123",
        "GitHub verarbeitet Update und sendet Response",
        "Agent erhält: ✅ Issue erfolgreich aktualisiert"
    ]

    for step in workflow:
        print(f"   {step}")

if __name__ == "__main__":
    test_universal_tool()
    simulate_agent_workflow()