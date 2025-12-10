#!/usr/bin/env python3
"""
Test-Script für echten GitHub API Call über das universelle Nango Tool
Testet das Auflisten von Repositories mit der gegebenen Connection-ID
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.universal_nango_api_tool import UniversalAPITool

def test_github_api_call():
    """Testet echten GitHub API Call zum Auflisten von Repositories"""

    print("🧪 Teste echten GitHub API Call über universelles Tool...")
    print("=" * 60)

    # Tool initialisieren
    tool = UniversalNangoAPITool()

    print(f"✅ Tool initialisiert: {tool.name}")

    # Connection-ID aus den Settings (bereits konfiguriert)
    from core.settings import settings
    print(f"🔗 Verwende Tyk Gateway: {settings.tyk_base_url}")

    print("\n" + "=" * 60)
    print("🚀 Führe GitHub API Call aus: GET /user/repos")
    print("   (Auflisten der Repositories des authentifizierten Users)")
    print()

    try:
        # API Call ausführen
        result = tool._run(
            provider="github",
            endpoint="/user/repos",
            method="GET",
            description="Liste alle Repositories des authentifizierten GitHub Users auf"
        )

        print("📋 API Response:")
        print("-" * 40)
        print(result)
        print("-" * 40)

        # Versuche JSON zu parsen und anzuzeigen
        try:
            import json
            if isinstance(result, str) and result.startswith('✅'):
                # Extrahiere JSON-Teil
                json_start = result.find('[')
                json_end = result.rfind(']') + 1
                if json_start != -1 and json_end != -1:
                    json_str = result[json_start:json_end]
                    repos = json.loads(json_str)
                    print(f"📊 Erfolgreich {len(repos)} Repositories gefunden!")

                    # Zeige erste 3 Repos
                    for i, repo in enumerate(repos[:3]):
                        print(f"   {i+1}. {repo.get('name', 'Unknown')} - {repo.get('description', 'No description')[:50]}...")
                else:
                    print("ℹ️  Response enthält kein JSON-Array")
            else:
                print("ℹ️  Response ist kein erfolgreicher API Call")
        except:
            print("ℹ️  Konnte Response nicht als JSON parsen")

        print("\n✅ GitHub API Call Test abgeschlossen!")

    except Exception as e:
        print(f"❌ Fehler bei GitHub API Call: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_github_api_call()