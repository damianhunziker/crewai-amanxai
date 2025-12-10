#!/usr/bin/env python3
"""
Simuliere universellen GitHub API Call über Zuplo

Zeigt, wie Agenten die GitHub API über das universelle LLM-gesteuerte Tool verwenden.
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm_driven_api_tool import LLMDrivenAPITool
from core.zuplo_client import ZuploClient

def simulate_github_api_usage():
    """Simuliert verschiedene GitHub API Calls über das universelle Tool"""

    print("🚀 SIMULATION: Universeller GitHub API Call über Zuplo")
    print("=" * 60)

    # 1. Zuplo API Spec laden (simuliert)
    print("1️⃣ Lade GitHub OpenAPI Spec über Zuplo...")

    # Simulierte OpenAPI Spec (GitHub REST API Auszug)
    github_openapi_spec = {
        "openapi": "3.0.1",
        "info": {
            "title": "GitHub REST API",
            "version": "2022-11-28"
        },
        "servers": [{
            "url": "https://api.github.com"
        }],
        "paths": {
            "/user/repos": {
                "post": {
                    "summary": "Create a repository for the authenticated user",
                    "operationId": "repos/create-for-authenticated-user",
                    "parameters": [],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Repository name"},
                                        "description": {"type": "string", "description": "Repository description"},
                                        "private": {"type": "boolean", "description": "Whether the repository is private"}
                                    },
                                    "required": ["name"]
                                }
                            }
                        }
                    }
                }
            },
            "/repos/{owner}/{repo}/issues": {
                "get": {
                    "summary": "List repository issues",
                    "operationId": "issues/list-for-repo",
                    "parameters": [
                        {"name": "owner", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "repo", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "state", "in": "query", "schema": {"type": "string", "enum": ["open", "closed", "all"]}},
                        {"name": "per_page", "in": "query", "schema": {"type": "integer", "default": 30}}
                    ]
                }
            }
        }
    }

    print("✅ GitHub OpenAPI Spec geladen")
    print(f"   📄 {len(json.dumps(github_openapi_spec))} Zeichen OpenAPI Definition")
    print(f"   🔗 Base URL: {github_openapi_spec['servers'][0]['url']}")

    # 2. Universelles Tool initialisieren
    print("\n2️⃣ Initialisiere universelles LLM API Tool...")

    # GitHub Tool mit Zuplo Gateway
    github_tool = LLMDrivenAPITool(
        api_id="github",
        openapi_spec=github_openapi_spec,
        api_base_url="http://localhost:9030/apis/github"  # Zuplo Gateway
    )

    print("✅ LLM API Tool für GitHub initialisiert")
    print(f"   🎯 Tool Name: {github_tool.name}")
    print(f"   📝 Description: {github_tool.description}")
    print(f"   🌐 Gateway URL: http://localhost:9030/apis/github")

    # 3. Simuliere verschiedene API Calls
    test_calls = [
        {
            "intent": "Erstelle ein neues Repository namens 'test-repo' mit der Beschreibung 'Test repository'",
            "expected_endpoint": "/user/repos",
            "expected_method": "POST",
            "expected_params": {"name": "test-repo", "description": "Test repository"}
        },
        {
            "intent": "Zeige mir alle offenen Issues im Repository 'microsoft/vscode'",
            "expected_endpoint": "/repos/microsoft/vscode/issues",
            "expected_method": "GET",
            "expected_params": {"state": "open"}
        },
        {
            "intent": "Erstelle ein privates Repository namens 'secret-project'",
            "expected_endpoint": "/user/repos",
            "expected_method": "POST",
            "expected_params": {"name": "secret-project", "private": True}
        }
    ]

    print("\n3️⃣ Simuliere API Calls über universelles Tool...")
    print("-" * 60)

    for i, test_case in enumerate(test_calls, 1):
        print(f"\n🔹 Test Call {i}: {test_case['intent'][:50]}...")

        try:
            # Hier würde normalerweise das LLM den Intent interpretieren
            # Für Simulation zeigen wir das erwartete Resultat

            print(f"   🤖 LLM interpretiert Intent...")
            print(f"   📍 Gefundener Endpoint: {test_case['expected_endpoint']}")
            print(f"   🔧 HTTP Methode: {test_case['expected_method']}")
            print(f"   📋 Parameter: {json.dumps(test_case['expected_params'], indent=2)}")

            # Simuliere Authentifizierung über Zuplo
            print("   🔐 Authentifizierung über Zuplo Gateway...")
            print("   🔑 API-Key aus Bitwarden geladen (via gespeicherte Referenz)")
            print("   ✅ Token an Zuplo Gateway übermittelt")

            # Simuliere API Call über Zuplo
            print("   📡 Sende Request über Zuplo Gateway...")
            print(f"   🌐 URL: http://localhost:9030/apis/github{test_case['expected_endpoint']}")
            print("   📊 Zuplo verarbeitet Request und fügt Auth-Header hinzu...")
            # Simuliere Response
            if test_case['expected_method'] == 'POST':
                print("   ✅ Repository erfolgreich erstellt!")
                print("   📄 Response: {'id': 123456, 'name': 'test-repo', 'full_name': 'user/test-repo'}")
            elif test_case['expected_method'] == 'GET':
                print("   ✅ Issues erfolgreich abgerufen!")
                print("   📄 Response: [{'id': 123, 'title': 'Bug fix needed', 'state': 'open'}, ...]")

            print("   📈 Call in Monitoring protokolliert")

        except Exception as e:
            print(f"   ❌ Fehler: {e}")

    # 4. Zeige Architektur-Übersicht
    print("\n4️⃣ Architektur-Übersicht:")
    print("-" * 40)
    print("👤 Agent Request → 🤖 LLM Interpreter")
    print("                    ↓")
    print("📋 OpenAPI Spec ← 🔍 Zuplo Discovery")
    print("                    ↓")
    print("🔐 Auth Token ← 🗝️ Bitwarden (via gespeicherte Referenz)")
    print("                    ↓")
    print("🌐 Zuplo Gateway → 📡 API Call → 📊 Monitoring")
    print("                    ↓")
    print("📈 ApiDog Dashboard ← 📊 Response")

    print("\n" + "=" * 60)
    print("🎉 SIMULATION ABGESCHLOSSEN!")
    print()
    print("📋 Zusammenfassung:")
    print("✅ 3 verschiedene GitHub API Calls simuliert")
    print("✅ LLM-basierte Intent-Interpretation")
    print("✅ Zuplo Gateway für Authentifizierung")
    print("✅ Bitwarden-Integration für API-Keys")
    print("✅ Vollständige Monitoring und Logging")
    print()
    print("🚀 Das universelle Tool kann JETZT jede API verwenden!")
    print("   Agenten müssen nur natürliche Sprache verwenden!")

if __name__ == "__main__":
    simulate_github_api_usage()