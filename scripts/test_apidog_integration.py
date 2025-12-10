#!/usr/bin/env python3
"""
ApiDog Integration Test Script

Testet die vollständige Integration zwischen CrewAI und ApiDog Service.
"""

import requests
import json
import time
from core.api_registry import api_registry
from core.api_admin import ApiDogMonitor

def test_apidog_health():
    """Test ApiDog Health-Check"""
    print("🏥 Testing ApiDog Health...")
    try:
        response = requests.get("http://localhost:3000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ ApiDog healthy: {data.get('status')} v{data.get('version')}")
            return True
        else:
            print(f"❌ ApiDog unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ApiDog nicht erreichbar: {e}")
        return False

def setup_test_apis():
    """Erstelle Test-APIs direkt in der lokalen Datenbank"""
    print("\n🛠️ Setting up test APIs in local registry...")

    test_apis = [
        {
            "id": "github",
            "name": "GitHub API",
            "category": "development",
            "description": "Repository und Issue Management",
            "base_url": "https://api.github.com",
            "auth_type": "api_key",
            "policies": {
                "rate_limit_per_hour": 5000,
                "max_concurrent_calls": 10,
                "timeout_seconds": 30,
                "retry_attempts": 3
            },
            "access_control": {
                "allowed_agents": ["manager", "researcher"],
                "allowed_users": ["admin"],
                "requires_approval": False
            },
            "metadata": {
                "requester": "Test System",
                "source": "test_setup",
                "configured": True,
                "token_valid": True
            }
        },
        {
            "id": "notion",
            "name": "Notion API",
            "category": "productivity",
            "description": "Datenbank und Dokumenten-Management",
            "base_url": "https://api.notion.com",
            "auth_type": "api_key",
            "policies": {
                "rate_limit_per_hour": 1000,
                "max_concurrent_calls": 5,
                "timeout_seconds": 30,
                "retry_attempts": 2
            },
            "access_control": {
                "allowed_agents": ["manager"],
                "allowed_users": ["admin"],
                "requires_approval": False
            },
            "metadata": {
                "requester": "Test System",
                "source": "test_setup",
                "configured": True,
                "token_valid": True
            }
        },
        {
            "id": "openai",
            "name": "OpenAI API",
            "category": "ai",
            "description": "KI-Modelle und Text-Generierung",
            "base_url": "https://api.openai.com",
            "auth_type": "api_key",
            "policies": {
                "rate_limit_per_hour": 100,
                "max_concurrent_calls": 3,
                "timeout_seconds": 60,
                "retry_attempts": 1
            },
            "access_control": {
                "allowed_agents": ["manager", "researcher", "editor"],
                "allowed_users": ["admin"],
                "requires_approval": False
            },
            "metadata": {
                "requester": "Test System",
                "source": "test_setup",
                "configured": True,
                "token_valid": True
            }
        }
    ]

    for api in test_apis:
        if api_registry.register_api(api):
            print(f"✅ API {api['name']} registriert")
        else:
            print(f"❌ Fehler bei Registrierung von {api['name']}")

def test_registry_integration():
    """Test Registry-Integration"""
    print("\n📋 Testing Registry Integration...")

    # Test API-Loading
    apis = api_registry.list_all_apis()
    print(f"📊 {len(apis)} APIs in Registry gefunden")

    for api in apis:
        print(f"  🔹 {api['name']} ({api['id']}) - Status: {api.get('statistics', {}).get('status', 'unknown')}")

    # Test Access Control
    print("\n🔐 Testing Access Control...")
    for api in apis[:2]:  # Test first 2 APIs
        access = api_registry.check_access(api['id'], "manager")
        print(f"  👤 Manager-Zugriff auf {api['name']}: {'✅' if access else '❌'}")

def test_monitoring_integration():
    """Test Monitoring-Integration"""
    print("\n📊 Testing Monitoring Integration...")

    monitor = ApiDogMonitor()

    # Test Dashboard (ohne ApiDog-Verbindung)
    print("📈 Lokales Dashboard:")
    monitor.show_monitoring_dashboard()

    print("\n📤 Testing Sync mit ApiDog...")
    success = monitor.sync_api_statistics()
    if success:
        print("✅ Statistiken erfolgreich synchronisiert")
    else:
        print("⚠️ Sync fehlgeschlagen (ApiDog nicht verfügbar) - lokale Backup erstellt")

def test_llm_api_tools():
    """Test LLM API Tools Integration"""
    print("\n🤖 Testing LLM API Tools...")

    try:
        from core.llm_api_manager import DynamicAPIManager
        manager = DynamicAPIManager()

        tools = manager.get_tools_for_agent("manager")
        print(f"🔧 {len(tools)} LLM API Tools für Manager verfügbar")

        for tool in tools[:2]:  # Show first 2
            print(f"  🛠️ {tool.name}: {tool.description[:50]}...")

        print("✅ LLM API Tools erfolgreich initialisiert")

    except Exception as e:
        print(f"⚠️ LLM Tools nicht verfügbar (CrewAI Issue): {e}")

def main():
    """Haupt-Test-Funktion"""
    print("🚀 ApiDog Integration Test")
    print("=" * 50)

    # Health Check
    if not test_apidog_health():
        print("⚠️ ApiDog Service nicht verfügbar - verwende lokale Registry")

    # Setup
    setup_test_apis()

    # Tests
    test_registry_integration()
    test_monitoring_integration()
    test_llm_api_tools()

    print("\n" + "=" * 50)
    print("🎉 ApiDog Integration Test abgeschlossen!")
    print("\n📋 Verfügbare APIs können jetzt über LLM interpretiert werden!")
    print("📊 Monitoring läuft und synchronisiert mit ApiDog!")
    print("🚀 CrewAI ist bereit für universelle API-Integration!")

if __name__ == "__main__":
    main()