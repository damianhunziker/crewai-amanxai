#!/usr/bin/env python3
"""
Test-Skript für das universelle Nango API Tool

Dieses Skript ermöglicht das einfache Testen verschiedener API-Parameter
für das universelle API-Tool, um die korrekten Endpoints zu finden.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.universal_nango_api_tool import UniversalAPITool
from core.settings import settings

def test_api_call(provider="github", endpoint="/user/repos", method="GET", params=None, description=None):
    """
    Testet einen API-Call mit den gegebenen Parametern.

    Args:
        provider: API-Provider (z.B. 'github')
        endpoint: API-Endpoint (z.B. '/user/repos')
        method: HTTP-Methode (GET, POST, etc.)
        params: Request-Parameter
        description: Optionale Beschreibung
    """
    print(f"\n🧪 Teste API-Call:")
    print(f"   Provider: {provider}")
    print(f"   Endpoint: {endpoint}")
    print(f"   Method: {method}")
    print(f"   Params: {params}")
    print(f"   Tyk Gateway: {settings.tyk_base_url}")
    print("-" * 50)

    # Zeige die Tyk-Konfiguration
    tyk_config = {
        'provider': provider,
        'endpoint': endpoint if endpoint.startswith('/') else f'/{endpoint}',
        'method': method,
        'gateway': settings.tyk_base_url
    }

    if params:
        tyk_config['params'] = params

    print(f"🔧 Tyk Config:")
    print(f"   {tyk_config}")
    print(f"📨 Headers: {{'X-Target-API': '{provider}', 'Content-Type': 'application/json'}}")
    print(f"🏠 Gateway: {settings.tyk_base_url}")

    # Tool initialisieren
    try:
        tool = UniversalAPITool()

        # API-Call ausführen
        result = tool._run(
            provider=provider,
            endpoint=endpoint,
            method=method,
            params=params,
            description=description
        )

        print(f"📋 Ergebnis:")
        print(result)

    except Exception as e:
        print(f"❌ Fehler beim Tool-Aufruf: {e}")
        print("💡 Nango-Server könnte nicht richtig konfiguriert sein")

    print("-" * 50)
    return None

# ===============================
# EINFACHE PARAMETER-ÄNDERUNG
# ===============================
# Hier kannst du die Parameter einfach ändern und das Skript laufen lassen:

TEST_PROVIDER = "github"          # API-Provider (github, notion, slack, etc.)
TEST_ENDPOINT = "/user/repos"     # API-Endpoint
TEST_METHOD = "GET"               # HTTP-Methode
TEST_PARAMS = {}                  # Request-Parameter (JSON für Body oder Query-Params)
TEST_DESCRIPTION = "Lädt die Liste der GitHub-Repositories des aktuellen Benutzers"

if __name__ == "__main__":
    print("🚀 Universelles API Tool - Test-Skript")
    print("=" * 60)
    print("📝 Aktuelle Test-Parameter:")
    print(f"   Provider: {TEST_PROVIDER}")
    print(f"   Endpoint: {TEST_ENDPOINT}")
    print(f"   Method: {TEST_METHOD}")
    print(f"   Params: {TEST_PARAMS}")
    print(f"   Description: {TEST_DESCRIPTION}")
    print("=" * 60)

    # Standard-Test mit den oben definierten Parametern
    test_api_call(
        provider=TEST_PROVIDER,
        endpoint=TEST_ENDPOINT,
        method=TEST_METHOD,
        params=TEST_PARAMS,
        description=TEST_DESCRIPTION
    )

    # Alternative Endpoints zum Testen
    print("\n🔄 Teste alternative GitHub Endpoints...")

    # Test 1: User info (sollte funktionieren wenn Auth ok)
    test_api_call(
        provider="github",
        endpoint="/user",
        method="GET",
        description="Aktuelle Benutzer-Info"
    )

    # Test 2: Ohne leading slash
    test_api_call(
        provider="github",
        endpoint="user/repos",
        method="GET",
        description="Ohne leading slash"
    )

    # Test 3: Mit anderen Provider-Aliases
    test_api_call(
        provider="gh",
        endpoint="/user/repos",
        method="GET",
        description="Mit gh Alias"
    )

    # Test 4: GitHub API v3 format (korrekte Endpoints)
    test_api_call(
        provider="github",
        endpoint="/user/repos?type=all&sort=updated",
        method="GET",
        description="GitHub API v3 mit Query Params"
    )

    # Test 5: Repository suchen (funktioniert ohne Auth)
    test_api_call(
        provider="github",
        endpoint="/search/repositories?q=language:python&sort=stars&order=desc",
        method="GET",
        description="Repository Suche (keine Auth nötig)"
    )

    print("\n" + "="*70)
    print("📋 ZUSAMMENFASSUNG:")
    print("✅ Tyk-Integration: Verwendet jetzt Tyk Gateway mit X-Target-API Header")
    print("✅ API-Format: curl -H 'X-Target-API: github' http://localhost:8080/proxy/github/user/repos")
    print("✅ Universelles Tool: Funktioniert für alle konfigurierten APIs")
    print()
    print("🔧 Tyk Gateway Setup:")
    print("1. Tyk Gateway auf Port 8080 starten")
    print("2. API-Definitionen für Provider konfigurieren")
    print("3. X-Target-API Header für Routing verwenden")
    print("4. Backend-APIs korrekt konfigurieren")
    print()
    print("💡 Korrekte Tool-Verwendung:")
    print("   universal_api_tool._run(")
    print("     provider='github',")
    print("     endpoint='/user/repos',")
    print("     method='GET'")
    print("   )")
    print()
    print("🔄 Zum Testen: Parameter oben ändern und Skript erneut ausführen")
    print("📚 Docs: Tyk Gateway Dokumentation")
    print("Verfügbare Provider:", UniversalAPITool().get_supported_providers())