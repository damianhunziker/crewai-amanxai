#!/usr/bin/env python3
"""
Check ApiDog Database Content

Überprüft den Inhalt der ApiDog-Datenbank und zeigt die gespeicherten Bitwarden-Referenzen.
"""

import sqlite3
import json
from datetime import datetime

def check_apidog_database(db_path="/Users/jgtcdghun/workspace/apidog/apidog.db"):
    """Überprüft den Inhalt der ApiDog-Datenbank"""

    print("🔍 CHECK APIDOG DATABASE CONTENT")
    print(f"📍 Datenbank: {db_path}")
    print("=" * 60)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Prüfe Tabellen
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 Tabellen gefunden: {[t[0] for t in tables]}")

        # Zeige API-Tabelle
        print("\n🔹 APIs TABELLE:")
        cursor.execute("SELECT id, name, bitwarden_item_id, bitwarden_item_name, bitwarden_collection_name FROM apis ORDER BY name")
        apis = cursor.fetchall()

        print("-" * 80)
        print("<15")
        print("-" * 80)

        for api in apis:
            print("<15")

        # Zeige API-Key-Mappings
        print("\n🔹 API-KEY-MAPPINGS TABELLE:")
        cursor.execute("SELECT api_id, bitwarden_item_id, bitwarden_item_name, bitwarden_collection_name, last_verified FROM api_key_mappings ORDER BY api_id")
        mappings = cursor.fetchall()

        if mappings:
            print("-" * 100)
            print("<12")
            print("-" * 100)

            for mapping in mappings:
                last_verified = mapping[4] or "Nie"
                print("<12")
        else:
            print("❌ Keine API-Key-Mappings gefunden")

        # Zeige Beispielhafte API-Details
        if apis:
            print("\n🔹 DETAILINFORMATIONEN (GitHub API):")
            cursor.execute("SELECT * FROM apis WHERE id = 'github'")
            github_api = cursor.fetchone()

            if github_api:
                columns = [desc[0] for desc in cursor.description]
                for i, col in enumerate(columns):
                    value = github_api[i]
                    if col in ['oauth_config', 'policies'] and value:
                        try:
                            parsed = json.loads(value)
                            print(f"  {col}: {json.dumps(parsed, indent=2)[:100]}...")
                        except:
                            print(f"  {col}: {value[:100]}...")
                    else:
                        print(f"  {col}: {value}")

        conn.close()

        print("\n" + "=" * 60)
        print("✅ Datenbank-Check erfolgreich abgeschlossen!")
        print(f"📊 {len(apis)} APIs mit Bitwarden-Referenzen gefunden")
        print(f"🔗 {len(mappings)} API-Key-Mappings gespeichert")

        return True

    except Exception as e:
        print(f"❌ Fehler beim Datenbank-Check: {e}")
        return False

if __name__ == "__main__":
    check_apidog_database()