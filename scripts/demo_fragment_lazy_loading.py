#!/usr/bin/env python3
"""
Demo of Fragment-Based Lazy Loading for OpenAPI Specifications.

This demo shows how LLMs can autonomously research and extract needed information
from OpenAPI specs using a fragment-based caching system.
"""

import json
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.api_fragment_cache import APIFragment, APIFragmentCache, fragment_cache


def demo_basic_fragment_operations():
    """Demo basic fragment storage and retrieval."""
    print("=" * 60)
    print("DEMO 1: Basic Fragment Operations")
    print("=" * 60)
    
    # Create a temporary database for demo
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    cache = APIFragmentCache(db_path)
    
    # Create a sample fragment
    fragment = APIFragment(
        fragment_id="github_get_user",
        api_id="github",
        fragment_type="endpoint",
        content={
            "path": "/user",
            "method": "GET",
            "operation": {
                "summary": "Get authenticated user",
                "description": "Returns the authenticated user's profile information",
                "parameters": [],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"}
                            }
                        }
                    }
                }
            }
        },
        metadata={
            "summary": "Get authenticated user",
            "description": "Returns the authenticated user's profile information",
            "keywords": ["user", "profile", "authenticated", "get"],
            "tags": ["users"]
        },
        created_at=datetime.now(),
        updated_at=datetime.now(),
        usage_count=0
    )
    
    # Store the fragment
    print("📦 Storing fragment...")
    success = cache.store_fragment(fragment)
    print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
    
    # Retrieve the fragment
    print("\n🔍 Retrieving fragment...")
    retrieved = cache.get_fragment("github_get_user")
    if retrieved:
        print(f"   ✅ Found fragment: {retrieved.fragment_id}")
        print(f"   API: {retrieved.api_id}")
        print(f"   Type: {retrieved.fragment_type}")
        print(f"   Path: {retrieved.content['path']}")
        print(f"   Method: {retrieved.content['method']}")
        print(f"   Usage count: {retrieved.usage_count}")
    else:
        print("   ❌ Fragment not found")
    
    # Find fragments by query
    print("\n🔎 Finding fragments by query...")
    from core.api_fragment_cache import FragmentQuery
    query = FragmentQuery(api_id="github", fragment_types=["endpoint"], limit=5)
    fragments = cache.find_fragments(query)
    print(f"   Found {len(fragments)} fragments")
    
    # Cleanup
    os.unlink(db_path)
    print("\n🧹 Cleaned up temporary database")


def demo_extract_from_openapi_spec():
    """Demo extracting fragments from an OpenAPI specification."""
    print("\n" + "=" * 60)
    print("DEMO 2: Extracting Fragments from OpenAPI Spec")
    print("=" * 60)
    
    # Create a temporary database
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    cache = APIFragmentCache(db_path)
    
    # Sample OpenAPI specification (simplified)
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "GitHub API",
            "version": "1.0.0",
            "description": "API for GitHub operations"
        },
        "paths": {
            "/user": {
                "get": {
                    "summary": "Get authenticated user",
                    "description": "Returns the authenticated user's profile information",
                    "operationId": "getUser",
                    "tags": ["users"],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    }
                }
            },
            "/repos/{owner}/{repo}/issues": {
                "get": {
                    "summary": "List repository issues",
                    "description": "Returns a list of issues for a repository",
                    "operationId": "listIssues",
                    "tags": ["issues", "repositories"],
                    "parameters": [
                        {
                            "name": "owner",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        },
                        {
                            "name": "repo",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Issue"}
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create an issue",
                    "description": "Creates a new issue in a repository",
                    "operationId": "createIssue",
                    "tags": ["issues"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/IssueCreate"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Issue created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Issue"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "login": {"type": "string"},
                        "name": {"type": "string"},
                        "email": {"type": "string"}
                    },
                    "description": "GitHub user object"
                },
                "Issue": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "state": {"type": "string", "enum": ["open", "closed"]}
                    },
                    "description": "GitHub issue object"
                },
                "IssueCreate": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "required": True},
                        "body": {"type": "string"}
                    },
                    "description": "Input for creating an issue"
                }
            }
        }
    }
    
    print("📄 Extracting fragments from OpenAPI spec...")
    fragments = cache.extract_fragments_from_spec("github", openapi_spec)
    
    print(f"   Extracted {len(fragments)} fragments")
    
    # Count by type
    endpoint_count = sum(1 for f in fragments if f.fragment_type == "endpoint")
    schema_count = sum(1 for f in fragments if f.fragment_type == "schema")
    
    print(f"   - Endpoints: {endpoint_count}")
    print(f"   - Schemas: {schema_count}")
    
    # Show some examples
    print("\n   Example fragments:")
    for i, fragment in enumerate(fragments[:3]):
        print(f"   {i+1}. {fragment.fragment_type.upper()}: {fragment.metadata.get('summary', fragment.content.get('name', 'N/A'))}")
    
    # Demonstrate intent-based search
    print("\n🔍 Searching fragments by intent...")
    print("   Intent: 'I want to create a new issue'")
    issue_fragments = cache.find_fragments_by_intent("github", "I want to create a new issue")
    print(f"   Found {len(issue_fragments)} relevant fragments")
    
    for fragment in issue_fragments[:2]:
        if fragment.fragment_type == "endpoint":
            print(f"   - {fragment.content['method']} {fragment.content['path']}: {fragment.metadata.get('summary', '')}")
        else:
            print(f"   - Schema: {fragment.content.get('name', 'N/A')}")
    
    # Get API statistics
    print("\n📊 API Statistics:")
    stats = cache.get_api_stats("github")
    print(f"   Total fragments: {stats.get('total_fragments', 0)}")
    print(f"   Fragment types: {stats.get('fragment_stats', {})}")
    
    # Cleanup
    os.unlink(db_path)


def demo_llm_autonomous_research_scenario():
    """Demo how an LLM could autonomously research API specs."""
    print("\n" + "=" * 60)
    print("DEMO 3: LLM Autonomous Research Scenario")
    print("=" * 60)
    
    print("🤖 Scenario: LLM needs to help user create a GitHub issue")
    print("   User says: 'I need to report a bug in my repository'")
    print("\n   LLM's thought process:")
    print("   1. Identify relevant API: GitHub API")
    print("   2. Search for fragments related to 'bug', 'issue', 'create'")
    print("   3. Load only relevant fragments (not the entire spec)")
    print("   4. Construct API call from fragments")
    
    # Simulate fragment cache with pre-loaded data
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    cache = APIFragmentCache(db_path)
    
    # Pre-load some fragments (simulating previously extracted data)
    fragments = [
        APIFragment(
            fragment_id="create_issue_endpoint",
            api_id="github",
            fragment_type="endpoint",
            content={
                "path": "/repos/{owner}/{repo}/issues",
                "method": "POST",
                "operation": {
                    "summary": "Create an issue",
                    "parameters": [
                        {"name": "owner", "in": "path", "required": True},
                        {"name": "repo", "in": "path", "required": True}
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/IssueCreate"}
                            }
                        }
                    }
                }
            },
            metadata={
                "summary": "Create an issue",
                "keywords": ["issue", "create", "bug", "report", "problem"],
                "tags": ["issues"]
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        APIFragment(
            fragment_id="issue_create_schema",
            api_id="github",
            fragment_type="schema",
            content={
                "name": "IssueCreate",
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "required": True},
                        "body": {"type": "string"},
                        "labels": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            metadata={
                "description": "Input for creating an issue",
                "keywords": ["issue", "create", "input", "schema"]
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]
    
    for fragment in fragments:
        cache.store_fragment(fragment)
    
    # LLM searches for relevant fragments
    print("\n   🔍 LLM searches fragment cache...")
    relevant_fragments = cache.find_fragments_by_intent("github", "report a bug in repository")
    
    print(f"   Found {len(relevant_fragments)} relevant fragments")
    
    # LLM builds context from fragments
    print("\n   🧩 LLM builds API call from fragments:")
    for fragment in relevant_fragments:
        if fragment.fragment_type == "endpoint":
            print(f"   - Endpoint: {fragment.content['method']} {fragment.content['path']}")
            print(f"     Summary: {fragment.metadata.get('summary', '')}")
            
            # Extract parameters
            if "parameters" in fragment.content.get("operation", {}):
                params = fragment.content["operation"]["parameters"]
                print(f"     Parameters: {[p['name'] for p in params]}")
            
            # Extract request body schema
            if "requestBody" in fragment.content.get("operation", {}):
                print(f"     Request body: Required")
        
        elif fragment.fragment_type == "schema":
            print(f"   - Schema: {fragment.content.get('name', 'N/A')}")
            print(f"     Description: {fragment.metadata.get('description', '')}")
    
    # LLM constructs final API call
    print("\n   🚀 LLM constructs API call:")
    print("   POST /repos/{owner}/{repo}/issues")
    print("   Body: {")
    print('     "title": "Bug report: ...",')
    print('     "body": "Description of the bug...",')
    print('     "labels": ["bug"]')
    print("   }")
    
    print("\n   ✅ LLM successfully researched API spec and constructed call")
    print("   without loading the entire OpenAPI specification!")
    
    # Cleanup
    os.unlink(db_path)


def demo_fragment_cache_performance():
    """Demo performance benefits of fragment-based caching."""
    print("\n" + "=" * 60)
    print("DEMO 4: Performance Benefits")
    print("=" * 60)
    
    print("📈 Traditional approach vs Fragment-based approach:")
    print("\n   Traditional:")
    print("   - Load entire OpenAPI spec (100+ KB)")
    print("   - Parse entire JSON/YAML")
    print("   - Search through all endpoints/schemas")
    print("   - Memory: High, Time: Slow")
    
    print("\n   Fragment-based:")
    print("   - Load only relevant fragments (1-5 KB)")
    print("   - Fast keyword/semantic search")
    print("   - Incremental loading as needed")
    print("   - Memory: Low, Time: Fast")
    
    print("\n   Benefits:")
    print("   - Faster response times for LLMs")
    print("   - Lower memory usage")
    print("   - Scalable to large API specs")
    print("   - Enables autonomous API research")


def main():
    """Run all demos."""
    print("🚀 Fragment-Based Lazy Loading Demo")
    print("=" * 60)
    print("How LLMs can autonomously research OpenAPI specifications")
    print("by loading only relevant fragments instead of entire specs.")
    print("=" * 60)
    
    try:
        demo_basic_fragment_operations()
        demo_extract_from_openapi_spec()
        demo_llm_autonomous_research_scenario()
        demo_fragment_cache_performance()
        
        print("\n" + "=" * 60)
        print("🎉 Demo Complete!")
        print("=" * 60)
        print("\nKey takeaways:")
        print("1. LLMs can research APIs autonomously using fragment cache")
        print("2. Only load needed parts of API specs (lazy loading)")
        print("3. Fast semantic search for relevant endpoints/schemas")
        print("4. Enables context-aware API call construction")
        print("5. Scalable solution for large API ecosystems")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
