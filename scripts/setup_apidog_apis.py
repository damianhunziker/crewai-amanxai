#!/usr/bin/env python3
"""
Setup Standard APIs in ApiDog Database

Fügt die wichtigsten APIs direkt in die ApiDog-Datenbank ein.
"""

import sqlite3
import json
from datetime import datetime

def setup_apidog_apis(db_path="/Users/jgtcdghun/workspace/apidog/apidog.db"):
    """Fügt Standard-APIs in ApiDog-Datenbank ein"""

    print("🚀 SETUP STANDARD APIs IN APIDOG DATABASE")
    print(f"📍 Datenbank: {db_path}")
    print("=" * 50)

    # Standard-API-Konfigurationen
    standard_apis = [
        {
            "id": "github",
            "name": "GitHub API",
            "category": "development",
            "description": "Repository und Issue Management, Pull Requests, Webhooks und GitHub Actions",
            "base_url": "https://api.github.com",
            "auth_type": "api_key",
            "policies": {
                "rate_limit_per_hour": 5000,
                "max_concurrent_calls": 10,
                "timeout_seconds": 30,
                "retry_attempts": 3,
                "auth_refresh": False
            },
            "oauth_config": {
                "authorization_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "scopes": ["repo", "user", "read:org"],
                "client_id": "",
                "redirect_uri": "http://localhost:3000/oauth/callback"
            }
        },
        {
            "id": "notion",
            "name": "Notion API",
            "category": "productivity",
            "description": "Datenbanken, Seiten und Blocks verwalten, Integration mit Notion Workspaces",
            "base_url": "https://api.notion.com",
            "auth_type": "api_key",
            "policies": {
                "rate_limit_per_hour": 1000,
                "max_concurrent_calls": 5,
                "timeout_seconds": 30,
                "retry_attempts": 2,
                "auth_refresh": False
            },
            "oauth_config": {}
        },
        {
            "id": "openai",
            "name": "OpenAI API",
            "category": "ai",
            "description": "GPT-Modelle, DALL-E Bildgenerierung, Embeddings und Moderation",
            "base_url": "https://api.openai.com",
            "auth_type": "api_key",
            "policies": {
                "rate_limit_per_hour": 100,
                "max_concurrent_calls": 3,
                "timeout_seconds": 60,
                "retry_attempts": 1,
                "auth_refresh": False
            },
            "oauth_config": {}
        },
        {
            "id": "slack",
            "name": "Slack API",
            "category": "communication",
            "description": "Messaging, Channels, Users und Bot-Integrationen verwalten",
            "base_url": "https://slack.com/api",
            "auth_type": "oauth2",
            "policies": {
                "rate_limit_per_hour": 1000,
                "max_concurrent_calls": 5,
                "timeout_seconds": 30,
                "retry_attempts": 2,
                "auth_refresh": True
            },
            "oauth_config": {
                "authorization_url": "https://slack.com/oauth/v2/authorize",
                "token_url": "https://slack.com/api/oauth.v2.access",
                "scopes": ["chat:write", "users:read", "channels:read", "files:write"],
                "client_id": "",
                "redirect_uri": "http://localhost:3000/oauth/callback"
            }
        },
        {
            "id": "discord",
            "name": "Discord API",
            "category": "communication",
            "description": "Bots, Webhooks und Server-Management für Discord",
            "base_url": "https://discord.com/api",
            "auth_type": "oauth2",
            "policies": {
                "rate_limit_per_hour": 5000,
                "max_concurrent_calls": 10,
                "timeout_seconds": 30,
                "retry_attempts": 3,
                "auth_refresh": True
            },
            "oauth_config": {
                "authorization_url": "https://discord.com/api/oauth2/authorize",
                "token_url": "https://discord.com/api/oauth2/token",
                "scopes": ["bot", "webhook.incoming", "guilds"],
                "client_id": "",
                "redirect_uri": "http://localhost:3000/oauth/callback"
            }
        },
        {
            "id": "google_calendar",
            "name": "Google Calendar API",
            "category": "productivity",
            "description": "Kalender verwalten, Events erstellen und synchronisieren",
            "base_url": "https://www.googleapis.com/calendar/v3",
            "auth_type": "oauth2",
            "policies": {
                "rate_limit_per_hour": 10000,
                "max_concurrent_calls": 20,
                "timeout_seconds": 30,
                "retry_attempts": 2,
                "auth_refresh": True
            },
            "oauth_config": {
                "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/calendar"],
                "client_id": "",
                "redirect_uri": "http://localhost:3000/oauth/callback"
            }
        },
        {
            "id": "stripe",
            "name": "Stripe API",
            "category": "payment",
            "description": "Zahlungen, Abonnements und Finanztransaktionen verwalten",
            "base_url": "https://api.stripe.com",
            "auth_type": "api_key",
            "policies": {
                "rate_limit_per_hour": 100000,
                "max_concurrent_calls": 50,
                "timeout_seconds": 30,
                "retry_attempts": 3,
                "auth_refresh": False
            },
            "oauth_config": {}
        },
        {
            "id": "twilio",
            "name": "Twilio API",
            "category": "communication",
            "description": "SMS, MMS, Voice-Calls und WhatsApp-Messaging",
            "base_url": "https://api.twilio.com",
            "auth_type": "api_key",
            "policies": {
                "rate_limit_per_hour": 10000,
                "max_concurrent_calls": 20,
                "timeout_seconds": 30,
                "retry_attempts": 2,
                "auth_refresh": False
            },
            "oauth_config": {}
        },
        {
            "id": "figma",
            "name": "Figma API",
            "category": "design",
            "description": "Design-Dateien, Components und Team-Management",
            "base_url": "https://api.figma.com",
            "auth_type": "oauth2",
            "policies": {
                "rate_limit_per_hour": 1000,
                "max_concurrent_calls": 5,
                "timeout_seconds": 30,
                "retry_attempts": 2,
                "auth_refresh": True
            },
            "oauth_config": {
                "authorization_url": "https://www.figma.com/api/oauth/authorize",
                "token_url": "https://www.figma.com/api/oauth/token",
                "scopes": ["files:read"],
                "client_id": "",
                "redirect_uri": "http://localhost:3000/oauth/callback"
            }
        },
        {
            "id": "wordpress",
            "name": "WordPress REST API",
            "category": "cms",
            "description": "Posts, Pages, Users und Custom Content verwalten",
            "base_url": "https://your-site.com/wp-json/wp/v2",
            "auth_type": "api_key",
            "policies": {
                "rate_limit_per_hour": 5000,
                "max_concurrent_calls": 10,
                "timeout_seconds": 30,
                "retry_attempts": 2,
                "auth_refresh": False
            },
            "oauth_config": {}
        }
    ]

    try:
        # Verbinde mit ApiDog-Datenbank
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("✅ ApiDog Datenbank verbunden")

        # Erstelle Tabellen falls sie nicht existieren
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS apis (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                description TEXT,
                base_url TEXT,
                openapi_spec_url TEXT,
                auth_type TEXT DEFAULT 'api_key',
                oauth_config TEXT,
                policies TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Füge neue Spalten hinzu falls sie nicht existieren
        try:
            cursor.execute('ALTER TABLE apis ADD COLUMN bitwarden_item_id TEXT')
        except:
            pass  # Spalte existiert bereits

        try:
            cursor.execute('ALTER TABLE apis ADD COLUMN bitwarden_item_name TEXT')
        except:
            pass  # Spalte existiert bereits

        try:
            cursor.execute("ALTER TABLE apis ADD COLUMN bitwarden_collection_name TEXT DEFAULT 'Vyftec Agenten'")
        except:
            pass  # Spalte existiert bereits

        # Neue Felder für verschiedene Auth-Typen
        try:
            cursor.execute('ALTER TABLE apis ADD COLUMN key_bw_id TEXT')  # Für API Keys
        except:
            pass

        try:
            cursor.execute('ALTER TABLE apis ADD COLUMN secret_bw_id TEXT')  # Für Secrets
        except:
            pass

        try:
            cursor.execute('ALTER TABLE apis ADD COLUMN token_bw_id TEXT')  # Für Tokens
        except:
            pass

        # Tabelle für API-Key-Mappings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_key_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_id TEXT NOT NULL,
                bitwarden_item_id TEXT NOT NULL,
                bitwarden_item_name TEXT NOT NULL,
                bitwarden_collection_name TEXT DEFAULT 'Vyftec Agenten',
                last_verified DATETIME,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (api_id) REFERENCES apis (id),
                UNIQUE(api_id)
            )
        ''')

        print("✅ Datenbank-Schema bereit")

        # Füge APIs ein
        inserted_count = 0
        updated_count = 0

        for api in standard_apis:
            try:
                # Prüfe ob API bereits existiert
                cursor.execute('SELECT id FROM apis WHERE id = ?', (api['id'],))
                exists = cursor.fetchone()

                if exists:
                    # Update existing API
                    cursor.execute('''
                        UPDATE apis SET
                            name = ?, category = ?, description = ?, base_url = ?,
                            openapi_spec_url = ?, auth_type = ?, oauth_config = ?, policies = ?,
                            bitwarden_item_id = ?, bitwarden_item_name = ?, bitwarden_collection_name = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (
                        api['name'], api['category'], api['description'], api['base_url'],
                        api.get('openapi_spec_url', ''), api['auth_type'],
                        json.dumps(api['oauth_config']), json.dumps(api['policies']),
                        api['id'], api['id'], 'Vyftec Agenten', api['id']
                    ))
                    updated_count += 1
                    print(f"✅ Updated: {api['name']}")
                else:
                    # Insert new API
                    cursor.execute('''
                        INSERT INTO apis (id, name, category, description, base_url, openapi_spec_url,
                                        auth_type, oauth_config, policies, bitwarden_item_id,
                                        bitwarden_item_name, bitwarden_collection_name)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        api['id'], api['name'], api['category'], api['description'], api['base_url'],
                        api.get('openapi_spec_url', ''), api['auth_type'],
                        json.dumps(api['oauth_config']), json.dumps(api['policies']),
                        api['id'], api['id'], 'Vyftec Agenten'
                    ))
                    inserted_count += 1
                    print(f"➕ Added: {api['name']}")

                # Erstelle/aktualisiere API-Key-Mapping
                cursor.execute('''
                    INSERT OR REPLACE INTO api_key_mappings
                    (api_id, bitwarden_item_id, bitwarden_item_name, bitwarden_collection_name, last_verified)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (api['id'], api['id'], api['id'], 'Vyftec Agenten'))

            except Exception as e:
                print(f"❌ Fehler bei API {api['id']}: {e}")

        conn.commit()
        conn.close()

        print("\n" + "=" * 50)
        print("🎉 API SETUP ABGESCHLOSSEN!")
        print(f"📊 Eingefügt: {inserted_count} neue APIs")
        print(f"🔄 Aktualisiert: {updated_count} bestehende APIs")
        print(f"📋 Gesamt: {len(standard_apis)} APIs verfügbar")
        print("\n🚀 ApiDog kann jetzt diese APIs verwalten!")
        print("=" * 50)

        return True

    except Exception as e:
        print(f"❌ Fehler beim Setup: {e}")
        return False

def verify_setup(db_path="/Users/jgtcdghun/workspace/apidog/apidog.db"):
    """Verifiziert das Setup"""
    print("\n🔍 VERIFIZIERUNG:")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM apis')
        count = cursor.fetchone()[0]

        cursor.execute('SELECT id, name, category, auth_type FROM apis ORDER BY name')
        apis = cursor.fetchall()

        print(f"📊 {count} APIs in Datenbank gefunden:")
        for api in apis:
            print(f"   🔹 {api[1]} ({api[0]}) - {api[2]} - {api[3]}")

        conn.close()

        if count >= 10:
            print("✅ Setup erfolgreich verifiziert!")
        else:
            print("⚠️ Weniger APIs als erwartet gefunden")

    except Exception as e:
        print(f"❌ Verifizierungsfehler: {e}")

if __name__ == "__main__":
    # Setup durchführen
    success = setup_apidog_apis()

    if success:
        # Verifizierung
        verify_setup()

        print("\n🎯 Nächste Schritte:")
        print("1. Starte ApiDog Service: cd /Users/jgtcdghun/workspace/apidog && npm start")
        print("2. Teste API-Zugriff: curl http://localhost:3000/apis")
        print("3. Integriere mit CrewAI: python main.py")