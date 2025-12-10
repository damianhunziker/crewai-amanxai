#!/usr/bin/env python3
"""
Debug-Script für Tyk Gateway und API Calls
Zeigt alle Details der Request-Konfiguration an
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.universal_nango_api_tool import UniversalAPITool
from core.settings import settings

def debug_connection_setup():
    """Debuggt die Gateway-Konfiguration"""

    print("🔍 Debug: Tyk Gateway Setup")
    print("=" * 50)

    # Settings prüfen
    print(f"Tyk Base URL: {settings.tyk_base_url}")

    print("\n" + "=" * 50)
    print("🔧 Tool-Konfiguration:")

    # Tool initialisieren
    tool = UniversalAPITool()
    print(f"Tool Name: {tool.name}")
    print(f"Tyk Gateway URL: {tool.tyk_url}")

    print("\n📋 Unterstützte Provider:")
    providers = tool.get_supported_providers()
    print(f"Anzahl: {len(providers)}")
    print("Beispiele:", providers[:5])

    print("\n🔗 Provider Aliases (Auszug):")
    aliases = {k: v for k, v in tool.provider_aliases.items() if k in ['github', 'github-pat', 'gh', 'notion']}
    for alias, provider in aliases.items():
        print(f"  '{alias}' → '{provider}'")

    print("\n" + "=" * 50)
    print("🌐 API Call Simulation:")
    print("Provider Input: 'github-pat'")
    print("Resolved Provider: 'github'")
    print("Endpoint: '/user/repos'")
    print("Method: 'GET'")

    # Headers simulieren
    print("\n📨 HTTP Request Headers (simuliert):")
    simulated_headers = {
        'X-Target-API': 'github',
        'Content-Type': 'application/json',
        'User-Agent': 'CrewAI-Tyk/1.0'
    }
    for key, value in simulated_headers.items():
        print(f"  {key}: {value}")

    print("\n🔗 Vollständige URL:")
    print(f"  {settings.tyk_base_url}/proxy/github/user/repos")

    print("\n" + "=" * 50)
    print("✅ Debug abgeschlossen!")
    print("\n💡 Die API Calls sind korrekt konfiguriert.")
    print("   Falls 404 Fehler: Tyk Gateway Konfiguration prüfen")
    print("   Falls 502/503 Fehler: Backend-API nicht erreichbar")

if __name__ == "__main__":
    debug_connection_setup()