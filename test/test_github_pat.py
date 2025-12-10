#!/usr/bin/env python3
"""
Test-Script für GitHub PAT Connection
Testet API Call mit github-pat als Provider
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.universal_nango_api_tool import UniversalAPITool

def test_github_pat():
    """Testet GitHub PAT Connection"""

    print("🧪 Teste GitHub PAT Connection...")
    print("=" * 60)

    # Tool initialisieren
    tool = UniversalNangoAPITool()

    print(f"✅ Tool initialisiert: {tool.name}")
    print(f"🔗 Nango Server: http://localhost:3003")

    print("\n" + "=" * 60)
    print("🚀 Teste GitHub PAT API Call: GET /user/repos")
    print("   Provider: github-pat")
    print("   Connection-ID: 8c88a265-f4ac-4c7b-96a6-d8526ac8eeaa")
    print()

    try:
        # API Call ausführen mit github-pat als Provider
        result = tool._run(
            provider="github-pat",  # Verwende github-pat statt github
            endpoint="/user/repos",
            method="GET",
            description="Liste alle Repositories des authentifizierten GitHub Users auf (PAT)"
        )

        print("📋 Nango API Response:")
        print("-" * 40)
        print(result)
        print("-" * 40)

        # Analysiere Response
        if result.startswith("❌"):
            print("❌ API Call fehlgeschlagen")
            if "HTTP 404" in result:
                print("💡 Mögliche Ursachen:")
                print("   - Provider-Key sollte 'github-pat' sein")
                print("   - Connection existiert, aber Provider-Key falsch")
                print("   - PAT Token hat nicht die nötigen Berechtigungen")
            elif "HTTP 401" in result:
                print("💡 Token-Authentifizierung fehlgeschlagen")
                print("   - PAT Token ist abgelaufen oder ungültig")
            elif "HTTP 403" in result:
                print("💡 Zugriff verweigert")
                print("   - PAT Token hat nicht die nötigen Scopes")
        else:
            print("✅ API Call erfolgreich!")
            # Versuche JSON zu parsen
            try:
                import json
                if "[" in result and "]" in result:
                    json_start = result.find("[")
                    json_end = result.rfind("]") + 1
                    if json_start != -1 and json_end != -1:
                        json_str = result[json_start:json_end]
                        repos = json.loads(json_str)
                        print(f"📊 {len(repos)} Repositories gefunden!")

                        # Zeige erste 3 Repos
                        for i, repo in enumerate(repos[:3]):
                            print(f"   {i+1}. {repo.get('name', 'Unknown')}")
                            print(f"      Private: {repo.get('private', 'Unknown')}")
                            print(f"      URL: {repo.get('html_url', 'N/A')}")
                            print()

            except:
                print("ℹ️  Konnte Response nicht als JSON parsen")

    except Exception as e:
        print(f"❌ Fehler bei GitHub PAT API Call: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("🎯 GitHub PAT Test abgeschlossen!")

    print("\n💡 Nächste Schritte:")
    print("   1. Prüfe in Nango Dashboard, ob Provider-Key 'github-pat' ist")
    print("   2. Stelle sicher, dass PAT Token gültig ist und 'repo' Scope hat")
    print("   3. Teste mit anderem Endpoint wie '/user' (einfacher)")

if __name__ == "__main__":
    test_github_pat()