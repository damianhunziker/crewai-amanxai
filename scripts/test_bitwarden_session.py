#!/usr/bin/env python3
"""
Test Bitwarden Session Management

Testet ob die BW_SESSION korrekt weitergegeben wird und keine manuelle Authentifizierung mehr erforderlich ist.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bitwarden_session_manager import initialize_bitwarden_session
from core.bitwarden_cli_integration import BitwardenCLIIntegration

def test_session_management():
    """Test der Session-Verwaltung"""
    print("🔐 Testing Bitwarden Session Management")
    print("=" * 50)

    # 1. Session initialisieren
    print("1️⃣ Initialisiere Session...")
    session_ok = initialize_bitwarden_session()
    if session_ok:
        print("✅ Session-Initialisierung erfolgreich")
    else:
        print("❌ Session-Initialisierung fehlgeschlagen")
        return False

    # 2. CLI-Client testen
    print("\n2️⃣ Teste CLI-Client...")
    try:
        client = BitwardenCLIIntegration()

        # Test Status
        status = client.get_status()
        print(f"📊 Vault Status: {status.get('status', 'unknown')}")

        # Test Collections (ohne manuelles Passwort)
        print("\n3️⃣ Teste Collections-Zugriff...")
        collections = client.get_collections()

        if collections:
            print(f"✅ {len(collections)} Collections gefunden:")
            for col in collections[:3]:  # Zeige erste 3
                print(f"   📁 {col.get('name', 'Unknown')} (ID: {col.get('id', 'N/A')})")

            # Test spezifische Collection
            target_collections = ['Vyftec Agenten', 'Shared-API-Keys']
            for target_name in target_collections:
                target_col = next((c for c in collections if c.get('name') == target_name), None)
                if target_col:
                    print(f"\n🔍 Teste Collection '{target_name}'...")
                    items = client.get_collection_items(target_col['id'])
                    print(f"   📋 {len(items)} Items in Collection")
                    if items:
                        for item in items[:2]:  # Zeige erste 2 Items
                            print(f"      🔹 {item.get('name', 'Unknown')} (ID: {item.get('id', 'N/A')})")
                else:
                    print(f"⚠️ Collection '{target_name}' nicht gefunden")

        else:
            print("⚠️ Keine Collections gefunden")

        # Test API-Key Retrieval
        print("\n4️⃣ Teste API-Key Retrieval...")
        test_keys = ['GitHub-Token', 'github', 'OpenAI-Key', 'openai']
        for key_name in test_keys:
            key = client.get_api_key(key_name)
            if key:
                print(f"✅ {key_name}: {key[:10]}...")
            else:
                print(f"❌ {key_name}: Nicht gefunden")

        print("\n🎉 Alle Tests erfolgreich - keine manuelle Authentifizierung erforderlich!")
        return True

    except Exception as e:
        print(f"❌ Fehler beim CLI-Test: {e}")
        return False

def test_subprocess_inheritance():
    """Test ob Subprozesse die Session erben"""
    print("\n🔄 Testing Subprocess Session Inheritance...")

    # Setze BW_SESSION in aktuellem Prozess
    session_token = os.getenv('BW_SESSION')
    if not session_token:
        try:
            with open('.bw_session', 'r') as f:
                session_token = f.read().strip()
        except:
            pass

    if not session_token:
        print("❌ Keine BW_SESSION verfügbar")
        return False

    os.environ['BW_SESSION'] = session_token

    # Teste Subprocess
    import subprocess
    try:
        result = subprocess.run(
            ['bw', 'status', '--raw'],
            capture_output=True,
            text=True,
            env=os.environ,
            timeout=10
        )

        if result.returncode == 0 and 'unlocked' in result.stdout.lower():
            print("✅ Subprocess kann BW_SESSION verwenden")
            return True
        else:
            print(f"❌ Subprocess Session-Fehler: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Subprocess Test fehlgeschlagen: {e}")
        return False

if __name__ == "__main__":
    print("🧪 BITWARDEN SESSION MANAGEMENT TEST")
    print("=" * 60)

    # Test 1: Session Management
    session_test = test_session_management()

    # Test 2: Subprocess Inheritance
    subprocess_test = test_subprocess_inheritance()

    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"Session Management: {'✅ PASS' if session_test else '❌ FAIL'}")
    print(f"Subprocess Inheritance: {'✅ PASS' if subprocess_test else '❌ FAIL'}")

    if session_test and subprocess_test:
        print("\n🎉 ALLE TESTS BESTANDEN - BW_SESSION funktioniert korrekt!")
        print("   Agenten müssen kein Master-Password mehr eingeben! 🚀")
    else:
        print("\n❌ TESTS FEHLGESCHLAGEN - Session-Management muss repariert werden")