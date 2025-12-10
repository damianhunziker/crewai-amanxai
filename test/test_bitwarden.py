#!/usr/bin/env python3
"""
Test script for Bitwarden CLI integration
Tests authentication, unlocking, and basic operations.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.bitwarden_session_manager import initialize_bitwarden_session, is_bitwarden_authenticated
from core.bitwarden_cli_integration import BitwardenCLIIntegration, test_bitwarden_cli_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_session_management():
    """Test Bitwarden session management."""
    print("🔐 Testing Bitwarden Session Management...")

    # Initialize session
    if initialize_bitwarden_session():
        print("✅ Session initialized successfully")
    else:
        print("❌ Session initialization failed")
        return False

    # Check authentication
    if is_bitwarden_authenticated():
        print("✅ Bitwarden is authenticated and unlocked")
        return True
    else:
        print("❌ Bitwarden is not authenticated or locked")
        return False

def test_cli_operations():
    """Test Bitwarden CLI operations."""
    print("\n🔧 Testing Bitwarden CLI Operations...")

    client = BitwardenCLIIntegration()

    # Test status
    print("📊 Testing status...")
    status = client.get_status()
    if status:
        print(f"✅ Status retrieved: {status.get('status', 'Unknown')}")
    else:
        print("❌ Failed to get status")

    # Test unlock (if needed)
    if status and status.get('status') == 'locked':
        print("🔓 Vault is locked, attempting unlock...")
        if client.unlock():
            print("✅ Vault unlocked successfully")
        else:
            print("❌ Failed to unlock vault")
            return False
    else:
        print("✅ Vault is already unlocked")

    # Test collections
    print("📁 Testing collections...")
    collections = client.get_collections()
    if collections:
        print(f"✅ Retrieved {len(collections)} collections: {[c['name'] for c in collections]}")
    else:
        print("❌ Failed to get collections")

    # Test API key retrieval (if available)
    print("🔑 Testing API key retrieval...")
    github_key = client.get_api_key("GitHub-Token")
    if github_key:
        print(f"✅ GitHub token retrieved: {github_key[:10]}...")
    else:
        print("⚠️ GitHub token not found (this is OK if not set up)")

    return True

def test_full_connection():
    """Test full connection using the test function."""
    print("\n🔗 Testing Full Connection...")

    results = test_bitwarden_cli_connection()
    print("📋 Connection Test Results:")
    for key, value in results.items():
        print(f"  {key}: {'✅' if value else '❌'} {value}")

    return all(results.values())

def main():
    """Main test function."""
    print("🧪 Bitwarden Integration Test Suite")
    print("=" * 50)

    # Check environment variables
    required_vars = ['BITWARDEN_AGENT_EMAIL', 'BITWARDEN_AGENT_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please set BITWARDEN_AGENT_EMAIL and BITWARDEN_AGENT_PASSWORD in .env")
        return False

    print(f"📧 Email: {os.getenv('BITWARDEN_AGENT_EMAIL')}")
    print(f"🔑 Password: {'*' * len(os.getenv('BITWARDEN_AGENT_PASSWORD', ''))}")

    # Run tests
    session_ok = test_session_management()
    cli_ok = test_cli_operations()
    connection_ok = test_full_connection()

    print("\n" + "=" * 50)
    if session_ok and cli_ok and connection_ok:
        print("🎉 All Bitwarden tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)