#!/usr/bin/env python3
"""
MCP SQLite Integration - GitHub API Eintrag erstellen

Verwendet MCP um einen GitHub-API-Eintrag in die ApiDog SQLite-Datenbank einzufügen.
"""

import json
import sys
from datetime import datetime

def create_github_api_entry():
    """Erstellt einen vollständigen GitHub-API-Eintrag"""

    github_api = {
        "id": "github",
        "name": "GitHub API",
        "category": "development",
        "description": "Vollständige GitHub API für Repository-Management, Issues, Pull Requests, Webhooks und GitHub Actions. Unterstützt alle REST-API-Endpunkte für Entwickler-Workflows.",
        "base_url": "https://api.github.com",
        "openapi_spec_url": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.yaml",
        "auth_type": "api_key",
        "oauth_config": json.dumps({
            "authorization_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "scopes": ["repo", "user", "read:org", "write:repo", "delete_repo"],
            "client_id": "",
            "redirect_uri": "http://localhost:3000/oauth/callback"
        }),
        "policies": json.dumps({
            "rate_limit_per_hour": 5000,
            "max_concurrent_calls": 10,
            "timeout_seconds": 30,
            "retry_attempts": 3,
            "auth_refresh": False,
            "cache_enabled": True,
            "audit_log": True
        })
    }

    return github_api

def generate_sql_insert(api_data):
    """Generiert SQL INSERT Statement"""

    sql = f"""
INSERT OR REPLACE INTO apis
(id, name, category, description, base_url, openapi_spec_url, auth_type, oauth_config, policies, created_at, updated_at)
VALUES
(
    '{api_data['id']}',
    '{api_data['name']}',
    '{api_data['category']}',
    '{api_data['description']}',
    '{api_data['base_url']}',
    '{api_data.get('openapi_spec_url', '')}',
    '{api_data['auth_type']}',
    '{api_data['oauth_config']}',
    '{api_data['policies']}',
    '{datetime.now().isoformat()}',
    '{datetime.now().isoformat()}'
);
"""

    return sql.strip()

def main():
    """Hauptfunktion"""
    print("🚀 MCP SQLite Integration - GitHub API Eintrag")
    print("=" * 60)

    # Erstelle API-Eintrag
    github_api = create_github_api_entry()

    print("📋 GitHub API Eintrag:")
    print(f"   ID: {github_api['id']}")
    print(f"   Name: {github_api['name']}")
    print(f"   Category: {github_api['category']}")
    print(f"   Base URL: {github_api['base_url']}")
    print(f"   Auth Type: {github_api['auth_type']}")
    print()

    # Generiere SQL
    sql_insert = generate_sql_insert(github_api)

    print("💾 SQL INSERT Statement:")
    print("-" * 40)
    print(sql_insert)
    print("-" * 40)
    print()

    # MCP verwenden um INSERT auszuführen
    print("🔧 Verwende MCP um Eintrag in Datenbank einzufügen...")
    print("📍 Datenbank: /Users/jgtcdghun/workspace/apidog/apidog.db")
    print()

    # MCP-Befehl für write_query
    mcp_command = {
        "method": "tools/call",
        "params": {
            "name": "write_query",
            "arguments": {
                "query": sql_insert
            }
        }
    }

    print("📤 MCP Command:")
    print(json.dumps(mcp_command, indent=2))
    print()

    print("✅ GitHub API Eintrag bereit für MCP-Execution!")
    print()
    print("📋 Zusammenfassung:")
    print(f"   🆔 API ID: {github_api['id']}")
    print(f"   📛 Name: {github_api['name']}")
    print(f"   🏷️  Kategorie: {github_api['category']}")
    print(f"   🔗 Base URL: {github_api['base_url']}")
    print(f"   🔐 Auth: {github_api['auth_type']}")
    print(f"   📊 Rate Limit: 5000/h")
    print()
    print("🎉 Bereit für MCP-Ausführung!")

if __name__ == "__main__":
    main()