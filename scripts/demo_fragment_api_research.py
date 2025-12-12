#!/usr/bin/env python3
"""
Demo: Wie LLMs OpenAPI-Spezifikationen selbstständig auslesen können.

Dieses Skript demonstriert, wie das fragment-basierte API-Tool es LLMs ermöglicht,
OpenAPI-Specs zu verstehen und API-Calls zu generieren, ohne dass spezifischer Code
für jede API geschrieben werden muss.
"""

import sys
import os
import sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fragment_based_api_tool import get_fragment_based_api_tool
from core.api_fragment_cache import fragment_cache

def demo_github_api_research():
    """Demo: GitHub API autonom erforschen."""
    print("🔍 Demo: GitHub API autonom erforschen")
    print("=" * 60)
    
    # Tool initialisieren
    tool = get_fragment_based_api_tool()
    
    # 1. User möchte ein Issue erstellen
    print("\n1. User Intent: 'I want to create a GitHub issue'")
    result = tool._run(
        user_intent="I want to create a GitHub issue",
        api_id="github",
        additional_params={"owner": "myorg", "repo": "myrepo"}
    )
    print(f"\nResult:\n{result}")
    
    # 2. User möchte User-Informationen abrufen
    print("\n2. User Intent: 'Get my GitHub user profile'")
    result = tool._run(
        user_intent="Get my GitHub user profile",
        api_id="github"
    )
    print(f"\nResult:\n{result}")
    
    # 3. Verfügbare Fragmente anzeigen
    print("\n3. Verfügbare Fragmente für GitHub:")
    fragments = tool.get_api_fragments("github", limit=10)
    print(fragments)
    
    return True

def demo_api_with_spec():
    """Demo: API mit OpenAPI-Spec erforschen."""
    print("\n🔍 Demo: API mit OpenAPI-Spec erforschen")
    print("=" * 60)
    
    tool = get_fragment_based_api_tool()
    
    # Beispiel OpenAPI Spec für eine fiktive Todo-API
    todo_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Todo API",
            "version": "1.0.0"
        },
        "paths": {
            "/todos": {
                "get": {
                    "summary": "Get all todos",
                    "description": "Returns a list of all todo items",
                    "responses": {
                        "200": {
                            "description": "Successful response"
                        }
                    }
                },
                "post": {
                    "summary": "Create a new todo",
                    "description": "Creates a new todo item",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "completed": {"type": "boolean", "default": False}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Todo created"
                        }
                    }
                }
            },
            "/todos/{id}": {
                "get": {
                    "summary": "Get todo by ID",
                    "description": "Returns a specific todo item",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response"
                        }
                    }
                },
                "put": {
                    "summary": "Update todo",
                    "description": "Updates an existing todo item",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True
                        }
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "completed": {"type": "boolean"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Todo updated"
                        }
                    }
                },
                "delete": {
                    "summary": "Delete todo",
                    "description": "Deletes a todo item",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True
                        }
                    ],
                    "responses": {
                        "204": {
                            "description": "Todo deleted"
                        }
                    }
                }
            }
        }
    }
    
    print("\nUser Intent: 'I need to create a new todo item'")
    result = tool._run(
        user_intent="I need to create a new todo item",
        api_id="todo",
        openapi_spec=todo_spec,
        additional_params={"title": "Buy groceries"}
    )
    print(f"\nResult:\n{result}")
    
    return True

def demo_agent_workflow():
    """Demo: Wie ein Agent das Tool verwendet."""
    print("\n🤖 Demo: Agent-Workflow mit Fragment-basiertem Tool")
    print("=" * 60)
    
    print("""
Szenario: Ein Agent muss eine unbekannte API integrieren.

Schritte:
1. Agent erhält User-Anfrage: "Create a new issue in my GitHub repository"
2. Agent identifiziert dies als API-Integrationsaufgabe
3. Agent verwendet das fragment_based_api_research Tool
4. Tool lädt nur relevante Fragmente der GitHub-API
5. Tool gibt API-Konfiguration zurück (Endpoint, Methode, Parameter)
6. Agent verwendet die Konfiguration für den API-Call
7. Agent aktualisiert Fragment-Statistiken für zukünftige Optimierung

Vorteile:
- Kein spezifischer Code für jede API nötig
- Nur relevante Teile der API-Spec werden geladen
- Lazy Loading reduziert Speicher- und Ladezeiten
- Fragment-Cache ermöglicht schnelle Wiederverwendung
- Confidence-Scores helfen bei der Entscheidungsfindung
""")
    
    # Cache-Statistiken anzeigen
    print("\n📊 Cache-Statistiken:")
    # Zeige Statistiken für alle APIs
    conn = sqlite3.connect("api_fragments.db")
    cursor = conn.cursor()
    
    # Gesamtanzahl der Fragmente
    cursor.execute("SELECT COUNT(*) FROM fragments")
    total_fragments = cursor.fetchone()[0]
    print(f"  Total fragments: {total_fragments}")
    
    # Fragmente pro API
    cursor.execute("SELECT api_id, COUNT(*) FROM fragments GROUP BY api_id")
    for api_id, count in cursor.fetchall():
        print(f"  {api_id}: {count} fragments")
    
    # Gesamtnutzung
    cursor.execute("SELECT SUM(usage_count) FROM fragments")
    total_usage = cursor.fetchone()[0] or 0
    print(f"  Total usage: {total_usage}")
    
    conn.close()
    
    return True

def demo_real_world_scenarios():
    """Demo: Reale Anwendungsfälle."""
    print("\n🌍 Demo: Reale Anwendungsfälle")
    print("=" * 60)
    
    tool = get_fragment_based_api_tool()
    
    scenarios = [
        {
            "name": "Notion API",
            "intent": "Create a new page in my Notion database",
            "api_id": "notion",
            "params": {"database_id": "my-db-id"}
        },
        {
            "name": "Slack API",
            "intent": "Send a message to a Slack channel",
            "api_id": "slack",
            "params": {"channel": "general"}
        },
        {
            "name": "Stripe API",
            "intent": "Create a new customer",
            "api_id": "stripe",
            "params": {"email": "customer@example.com"}
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📋 {scenario['name']}:")
        print(f"   Intent: {scenario['intent']}")
        
        # In einer echten Implementierung würde hier das Tool aufgerufen werden
        # Für die Demo zeigen wir nur das Konzept
        print(f"   → Tool würde {scenario['api_id']}-Fragmente laden")
        print(f"   → Confidence-Score berechnen")
        print(f"   → API-Call-Konfiguration zurückgeben")
    
    return True

def main():
    """Hauptfunktion der Demo."""
    print("🚀 Fragment-Based API Research Demo")
    print("=" * 60)
    print("Wie LLMs OpenAPI-Spezifikationen selbstständig auslesen können")
    print("=" * 60)
    
    try:
        # Demo 1: GitHub API
        demo_github_api_research()
        
        # Demo 2: API mit Spec
        demo_api_with_spec()
        
        # Demo 3: Agent-Workflow
        demo_agent_workflow()
        
        # Demo 4: Reale Szenarien
        demo_real_world_scenarios()
        
        print("\n" + "=" * 60)
        print("🎉 Demo abgeschlossen!")
        print("\nZusammenfassung:")
        print("1. LLMs können APIs autonom erforschen")
        print("2. Fragment-basiertes Lazy Loading reduziert Overhead")
        print("3. Confidence-Scores helfen bei der Entscheidungsfindung")
        print("4. Cache-Statistiken optimieren die Performance")
        print("5. Kein spezifischer Code für jede API nötig")
        print("\nDas System ermöglicht es Agenten, jede API zu nutzen,")
        print("die über OpenAPI-Specs verfügbar ist - vollständig autonom!")
        
    except Exception as e:
        print(f"\n❌ Demo fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
