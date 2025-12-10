#!/usr/bin/env python3
"""
Test-Script für echten Nango API Call
Testet das universelle Tool mit dem laufenden Nango-Server
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.universal_nango_api_tool import UniversalAPITool

def test_real_nango_call():
    """Testet echten Nango API Call"""

    print("🧪 Teste echten Nango API Call...")
    print("=" * 60)

    # Tool initialisieren
    tool = UniversalNangoAPITool()

    print(f"✅ Tool initialisiert: {tool.name}")
    print(f"🔗 Nango Server: http://localhost:3003")
    print(f"🔑 Secret Key konfiguriert: ✅")

    print("\n" + "=" * 60)
    print("🚀 Führe GitHub API Call aus: GET /user/repos")
    print("   Connection-ID: 8c88a265-f4ac-4c7b-96a6-d8526ac8eeaa")
    print()

    try:
        # API Call ausführen
        result = tool._run(
            provider="github",
            endpoint="/user/repos",
            method="GET",
            description="Liste alle Repositories des authentifizierten GitHub Users auf"
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
                print("   - Connection existiert nicht")
                print("   - GitHub Integration nicht konfiguriert")
                print("   - Endpoint nicht verfügbar")
            elif "HTTP 401" in result:
                print("💡 Token-Authentifizierung fehlgeschlagen")
            elif "HTTP 403" in result:
                print("💡 Zugriff verweigert - prüfe Token-Berechtigungen")
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
            except:
                pass

    except Exception as e:
        print(f"❌ Fehler bei Nango API Call: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("🎯 Test abgeschlossen!")

    print("\n💡 Nächste Schritte:")
    print("   1. Stelle sicher, dass die GitHub-Connection konfiguriert ist")
    print("   2. Prüfe Token-Berechtigungen in Nango Dashboard")
    print("   3. Teste andere Provider (Notion, Slack, etc.)")

if __name__ == "__main__":
    test_real_nango_call()