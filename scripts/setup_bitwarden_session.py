#!/usr/bin/env python3
"""
Setup Bitwarden Session Automatically

Führt automatisches Login durch und richtet persistente BW_SESSION ein.
Muss nur einmal ausgeführt werden oder wenn die Session abläuft.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bitwarden_session_manager import session_manager
from core.bitwarden_cli_integration import BitwardenCLIIntegration

def setup_bitwarden_session():
    """Richtet Bitwarden-Session automatisch ein"""
    print("🔐 AUTOMATISCHES BITWARDEN SESSION SETUP")
    print("=" * 50)

    # 1. Prüfe ob Credentials konfiguriert sind
    email = os.getenv('BITWARDEN_AGENT_EMAIL')
    password = os.getenv('BITWARDEN_AGENT_PASSWORD')

    if not email or not password:
        print("❌ Bitwarden-Credentials nicht konfiguriert!")
        print("Bitte in .env setzen:")
        print("BITWARDEN_AGENT_EMAIL=deine@email.com")
        print("BITWARDEN_AGENT_PASSWORD=dein-password")
        return False

    print(f"📧 Email: {email}")
    print("🔑 Password: [KONFIGURIERT]")

    # 2. Teste bestehende Session
    print("\n🔍 Prüfe bestehende Session...")
    if session_manager.check_session_validity():
        print("✅ Bestehende Session ist gültig")
        return True

    # 3. Führe Login durch
    print("\n🔐 Führe Login durch...")
    try:
        client = BitwardenCLIIntegration()

        # Versuche 2FA-Login zuerst
        if client.login_with_2fa():
            print("✅ Login mit 2FA erfolgreich")
        elif client.login():
            print("✅ Login erfolgreich")
        else:
            print("❌ Login fehlgeschlagen")
            print("Überprüfe Email und Password in .env")
            return False

        # 4. Verifiziere Session
        print("\n🔍 Verifiziere Session...")
        if session_manager.check_session_validity():
            print("✅ Session ist gültig")

            # 5. Teste API-Zugriff
            print("\n🧪 Teste API-Zugriff...")
            collections = client.get_collections()
            if collections:
                print(f"✅ {len(collections)} Collections verfügbar")
                for col in collections:
                    print(f"   📁 {col.get('name')}")

                # Teste API-Keys
                test_keys = ['GitHub-Token', 'github', 'OpenAI-Key', 'openai']
                found_keys = 0
                for key_name in test_keys:
                    key = client.get_api_key(key_name)
                    if key:
                        print(f"   🔑 {key_name}: ✅ Gefunden")
                        found_keys += 1
                    else:
                        print(f"   🔑 {key_name}: ❌ Nicht gefunden")

                if found_keys > 0:
                    print(f"\n✅ {found_keys} API-Keys verfügbar")
                else:
                    print("\n⚠️ Keine API-Keys gefunden - füge sie in Bitwarden hinzu")

            print("\n🎉 BITWARDEN SESSION ERFOLGREICH EINGERICHTET!")
            print("Deine Agenten können jetzt ohne manuelle Authentifizierung arbeiten! 🚀")

            return True
        else:
            print("❌ Session-Validierung fehlgeschlagen")
            return False

    except Exception as e:
        print(f"❌ Fehler beim Setup: {e}")
        return False

def show_session_info():
    """Zeigt Session-Informationen an"""
    print("\n📊 SESSION INFORMATIONEN:")
    print("-" * 30)

    session_token = os.getenv('BW_SESSION')
    if session_token:
        print(f"🔑 BW_SESSION: {session_token[:20]}...{session_token[-10:]}")
    else:
        print("❌ BW_SESSION nicht gesetzt")

    session_file = '.bw_session'
    if os.path.exists(session_file):
        try:
            with open(session_file, 'r') as f:
                file_session = f.read().strip()
            print(f"💾 Session-Datei: {session_file} ({len(file_session)} Zeichen)")
        except Exception as e:
            print(f"❌ Session-Datei Fehler: {e}")
    else:
        print("❌ Session-Datei nicht gefunden")

if __name__ == "__main__":
    print("🚀 BITWARDEN AUTOMATIC SESSION SETUP")
    print("=" * 60)

    # Zeige aktuelle Session-Info
    show_session_info()

    # Führe Setup durch
    if setup_bitwarden_session():
        print("\n" + "=" * 60)
        print("🎉 ERFOLG! Du kannst jetzt CrewAI ohne manuelle Authentifizierung starten:")
        print("   python main.py")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ SETUP FEHLGESCHLAGEN")
        print("Überprüfe deine Bitwarden-Credentials in .env")
        print("=" * 60)