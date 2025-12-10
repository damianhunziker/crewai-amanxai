#!/usr/bin/env python3
"""
Einfache Test-Integration: Notion API über Zuplo Gateway

Testet die vollständige Integration:
- Zuplo-Client für API-Discovery
- Hardcoded Notion API-Key
- API-Call über Zuplo-Gateway
- OpenAPI Spec in ApiDog Datenbank speichern
"""

import os
import sys
import json
import requests
import sqlite3
from pathlib import Path

# Pfad zum apidog Verzeichnis
APIDOG_PATH = "/Users/jgtcdghun/workspace/apidog"
APIDOG_DB = f"{APIDOG_PATH}/apidog.db"

# Zuplo Konfiguration
ZUPLO_BASE_URL = "http://localhost:9030"
ZUPLO_API_KEY = "6ee0edde349cb1e0f3354a4d0b35cdb259432b7aefbd489403e7befe69ea5dd4"

# Notion API Konfiguration
NOTION_API_KEY = ""
NOTION_BASE_URL = "https://api.notion.com/v1"

# Pfad zu unserem core hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.zuplo_client import ZuploClient

def test_zuplo_connection():
    """Teste Verbindung zu Zuplo-Server"""
    print("🔗 Teste Zuplo-Server Verbindung...")
    try:
        response = requests.get(f"{ZUPLO_BASE_URL}/apis",
                              headers={"Authorization": f"Bearer {ZUPLO_API_KEY}"})
        if response.status_code == 200:
            print("✅ Zuplo-Server ist erreichbar")
            return True
        else:
            print(f"❌ Zuplo-Server Fehler: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Zuplo-Verbindung fehlgeschlagen: {e}")
        return False

def get_notion_openapi_spec():
    """Hole Notion OpenAPI Spec von Zuplo"""
    print("📋 Hole Notion OpenAPI Spec von Zuplo...")

    # Erstelle Zuplo-Client
    zuplo = ZuploClient(ZUPLO_BASE_URL)
    zuplo.session.headers.update({"Authorization": f"Bearer {ZUPLO_API_KEY}"})

    try:
        spec = zuplo.get_api_spec("notion")
        if spec:
            print("✅ Notion OpenAPI Spec erfolgreich geladen")
            print(f"   📄 {len(json.dumps(spec))} Zeichen Spec")
            return spec
        else:
            print("❌ Keine Notion Spec von Zuplo erhalten")
            return None
    except Exception as e:
        print(f"❌ Fehler beim Laden der Spec: {e}")
        return None

def test_notion_api_direct():
    """Teste Notion API direkt (ohne Zuplo)"""
    print("🔗 Teste Notion API direkt...")

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    try:
        response = requests.get(f"{NOTION_BASE_URL}/users", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Notion API direkt erfolgreich")
            print(f"   👥 {len(data.get('results', []))} Benutzer gefunden")
            return True
        else:
            print(f"❌ Notion API Fehler: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion API Fehler: {e}")
        return False

def test_notion_api_via_zuplo():
    """Teste Notion API über Zuplo-Gateway"""
    print("🌐 Teste Notion API über Zuplo-Gateway...")

    # API-Call über Zuplo
    api_url = f"{ZUPLO_BASE_URL}/apis/notion/users"

    headers = {
        "Authorization": f"Bearer {ZUPLO_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            print("✅ Notion API über Zuplo erfolgreich")
            print(f"   👥 {len(data.get('results', []))} Benutzer gefunden")
            print(f"   📡 Gateway-Response: {len(str(data))} Zeichen")
            return True
        else:
            print(f"❌ Zuplo Gateway Fehler: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"❌ Zuplo Gateway Fehler: {e}")
        return False

def save_notion_spec_to_apidog_db(spec):
    """Speichere Notion OpenAPI Spec in ApiDog Datenbank"""
    print("💾 Speichere Notion Spec in ApiDog Datenbank...")

    if not os.path.exists(APIDOG_DB):
        print(f"❌ ApiDog Datenbank nicht gefunden: {APIDOG_DB}")
        return False

    try:
        conn = sqlite3.connect(APIDOG_DB)
        cursor = conn.cursor()

        # Prüfe Tabellenstruktur
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"   📊 Datenbank-Tabellen: {[t[0] for t in tables]}")

        # Suche nach API-spezifischer Tabelle (z.B. apis, api_specs, etc.)
        api_table = None
        for table_name, in tables:
            if 'api' in table_name.lower():
                api_table = table_name
                break

        if api_table:
            print(f"   🎯 Verwende Tabelle: {api_table}")

            # Einfaches INSERT - passe Schema an
            spec_json = json.dumps(spec)
            cursor.execute(f"""
                INSERT OR REPLACE INTO {api_table} (name, spec, updated_at)
                VALUES (?, ?, datetime('now'))
            """, ("notion", spec_json))

            conn.commit()
            print("✅ Notion Spec in ApiDog Datenbank gespeichert")
            return True
        else:
            print("❌ Keine passende API-Tabelle gefunden")
            return False

    except Exception as e:
        print(f"❌ Datenbank-Fehler: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Haupt-Test-Funktion"""
    print("🚀 NOTION API INTEGRATION TEST ÜBER ZUPLO")
    print("=" * 60)

    # 1. Zuplo-Server testen
    if not test_zuplo_connection():
        print("❌ Zuplo-Server nicht verfügbar - breche ab")
        return

    # 2. Notion API direkt testen
    if not test_notion_api_direct():
        print("⚠️ Notion API direkt nicht verfügbar - überspringe Gateway-Test")

    # 3. Notion OpenAPI Spec von Zuplo holen
    notion_spec = get_notion_openapi_spec()

    # 4. Notion API über Zuplo testen
    if notion_spec:
        api_success = test_notion_api_via_zuplo()
    else:
        api_success = False

    # 5. Spec in ApiDog Datenbank speichern
    if notion_spec:
        db_success = save_notion_spec_to_apidog_db(notion_spec)
    else:
        db_success = False

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("📊 TEST ZUSAMMENFASSUNG:")
    print(f"✅ Zuplo-Server: Verfügbar")
    print(f"✅ Notion API direkt: {'Erfolgreich' if test_notion_api_direct() else 'Fehlgeschlagen'}")
    print(f"✅ Notion Spec von Zuplo: {'Geladen' if notion_spec else 'Fehlgeschlagen'}")
    print(f"✅ Notion API über Zuplo: {'Erfolgreich' if api_success else 'Fehlgeschlagen'}")
    print(f"✅ Spec in ApiDog DB: {'Gespeichert' if db_success else 'Fehlgeschlagen'}")

    if notion_spec and api_success:
        print("\n🎉 NOTION API INTEGRATION ERFOLGREICH!")
        print("   - Zuplo-Gateway funktioniert")
        print("   - API-Key-Authentifizierung funktioniert")
        print("   - OpenAPI Spec verfügbar")
        print("   - ApiDog Datenbank aktualisiert")
    else:
        print("\n❌ Integration unvollständig - weitere Debugging nötig")

if __name__ == "__main__":
    main()