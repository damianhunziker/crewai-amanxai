#!/usr/bin/env python3
"""
Test script to demonstrate how agents can use the fragment-based API tool.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fragment_based_api_tool import get_fragment_based_api_tool


def test_fragment_tool_basic():
    """Test basic usage of the fragment-based API tool."""
    print("🧪 Testing Fragment-Based API Tool")
    print("=" * 60)
    
    # Get the tool
    tool = get_fragment_based_api_tool()
    
    print(f"Tool name: {tool.name}")
    print(f"Tool description: {tool.description}")
    
    # Test 1: Basic API research
    print("\n1. Basic API Research Test:")
    print("   Intent: 'I want to create a GitHub issue'")
    print("   API: 'github'")
    
    result = tool._run(
        user_intent="I want to create a GitHub issue",
        api_id="github",
        openapi_spec=None,  # No spec provided - will use existing fragments
        additional_params={"priority": "high"}
    )
    
    print(f"\n   Result:\n{result}")
    
    # Test 2: Get available fragments
    print("\n2. Get Available Fragments Test:")
    fragments_info = tool.get_api_fragments("github", limit=5)
    print(f"\n   Available fragments:\n{fragments_info}")
    
    # Test 3: Cleanup old fragments
    print("\n3. Cleanup Old Fragments Test:")
    cleanup_result = tool.cleanup_fragments(days_old=30)
    print(f"\n   Cleanup result: {cleanup_result}")
    
    print("\n" + "=" * 60)
    print("✅ Fragment tool tests completed")
    
    return True


def test_fragment_tool_with_spec():
    """Test fragment tool with OpenAPI specification."""
    print("\n🧪 Testing Fragment Tool with OpenAPI Spec")
    print("=" * 60)
    
    tool = get_fragment_based_api_tool()
    
    # Sample OpenAPI spec for GitHub
    github_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "GitHub API",
            "version": "1.0.0"
        },
        "paths": {
            "/user": {
                "get": {
                    "summary": "Get authenticated user",
                    "description": "Returns the authenticated user's profile",
                    "responses": {
                        "200": {
                            "description": "Successful response"
                        }
                    }
                }
            },
            "/repos/{owner}/{repo}/issues": {
                "post": {
                    "summary": "Create an issue",
                    "description": "Creates a new issue in a repository",
                    "parameters": [
                        {
                            "name": "owner",
                            "in": "path",
                            "required": True
                        },
                        {
                            "name": "repo",
                            "in": "path",
                            "required": True
                        }
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "body": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Issue created"
                        }
                    }
                }
            }
        }
    }
    
    print("Testing with provided OpenAPI spec...")
    result = tool._run(
        user_intent="Create a new issue in my repository",
        api_id="github",
        openapi_spec=github_spec,
        additional_params={"owner": "myorg", "repo": "myrepo"}
    )
    
    print(f"\nResult:\n{result}")
    
    print("\n" + "=" * 60)
    print("✅ Fragment tool with spec test completed")
    
    return True


def demonstrate_agent_usage():
    """Demonstrate how an agent would use the tool."""
    print("\n🤖 Agent Usage Demonstration")
    print("=" * 60)
    
    print("Scenario: Agent needs to help user with API integration")
    print("\nAgent's thought process:")
    print("1. User says: 'I need to integrate with the GitHub API to manage issues'")
    print("2. Agent identifies this as an API research task")
    print("3. Agent uses fragment_based_api_research tool")
    print("4. Tool loads only relevant fragments (not entire spec)")
    print("5. Tool returns API call configuration")
    print("6. Agent uses the configuration to make the API call")
    
    print("\nExample tool call:")
    print("""
    tool_input = {
        "user_intent": "I need to create and list GitHub issues",
        "api_id": "github",
        "additional_params": {"organization": "my-org"}
    }
    
    result = fragment_based_api_research._run(**tool_input)
    """)
    
    print("\nExpected output includes:")
    print("- Recommended API endpoints")
    print("- Required parameters")
    print("- Confidence score")
    print("- Fragment usage statistics")
    print("- Next steps")
    
    print("\n" + "=" * 60)
    print("✅ Agent usage demonstration completed")


if __name__ == "__main__":
    try:
        print("🚀 Fragment-Based API Tool Test Suite")
        print("=" * 60)
        
        # Run tests
        test_fragment_tool_basic()
        test_fragment_tool_with_spec()
        demonstrate_agent_usage()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        print("\nKey takeaways:")
        print("1. Agents can research APIs autonomously")
        print("2. Only relevant fragments are loaded (lazy loading)")
        print("3. Tool provides confidence scores and reasoning")
        print("4. Statistics help optimize fragment usage")
        print("5. Enables autonomous API integration")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
