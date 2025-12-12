"""
Tests for the API Fragment Cache System.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from core.api_fragment_cache import (
    APIFragment, FragmentQuery, APIFragmentCache, fragment_cache
)

# Mock the LLM imports to avoid API key requirements
import sys
import importlib

# Temporarily mock the problematic imports
sys.modules['core.openapi_llm_interpreter_fragment'] = MagicMock()
sys.modules['core.openapi_llm_interpreter_fragment'].get_llm_for_api_interpretation = MagicMock()
sys.modules['core.openapi_llm_interpreter_fragment'].OpenAPILLMInterpreter = MagicMock()

# Now import the actual module
from core.openapi_llm_interpreter_fragment import (
    FragmentBasedOpenAPILLMInterpreter, FragmentBasedAPICallConfig
)


class TestAPIFragment:
    """Tests for APIFragment dataclass."""
    
    def test_fragment_creation(self):
        """Test creating an APIFragment."""
        fragment = APIFragment(
            fragment_id="test_id",
            api_id="github",
            fragment_type="endpoint",
            content={"path": "/user", "method": "GET"},
            metadata={"summary": "Get user"},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert fragment.fragment_id == "test_id"
        assert fragment.api_id == "github"
        assert fragment.fragment_type == "endpoint"
        assert fragment.content["path"] == "/user"
        assert fragment.metadata["summary"] == "Get user"
    
    def test_to_dict(self):
        """Test converting fragment to dictionary."""
        fragment = APIFragment(
            fragment_id="test_id",
            api_id="github",
            fragment_type="endpoint",
            content={"path": "/user"},
            metadata={"summary": "Get user"},
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        fragment_dict = fragment.to_dict()
        assert fragment_dict["fragment_id"] == "test_id"
        assert fragment_dict["api_id"] == "github"
        assert fragment_dict["created_at"] == "2024-01-01T12:00:00"


class TestAPIFragmentCache:
    """Tests for APIFragmentCache class."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        cache = APIFragmentCache(db_path)
        yield cache
        
        # Cleanup
        os.unlink(db_path)
    
    def test_init_database(self, temp_db):
        """Test database initialization."""
        # Database should be initialized by fixture
        assert os.path.exists(temp_db.db_path)
    
    def test_store_and_retrieve_fragment(self, temp_db):
        """Test storing and retrieving a fragment."""
        fragment = APIFragment(
            fragment_id="test_fragment_1",
            api_id="github",
            fragment_type="endpoint",
            content={"path": "/user", "method": "GET"},
            metadata={"summary": "Get user info"},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store fragment
        result = temp_db.store_fragment(fragment)
        assert result is True
        
        # Retrieve fragment
        retrieved = temp_db.get_fragment("test_fragment_1")
        assert retrieved is not None
        assert retrieved.fragment_id == "test_fragment_1"
        assert retrieved.api_id == "github"
        assert retrieved.content["path"] == "/user"
    
    def test_find_fragments(self, temp_db):
        """Test finding fragments by query."""
        # Create test fragments
        for i in range(5):
            fragment = APIFragment(
                fragment_id=f"test_fragment_{i}",
                api_id="github",
                fragment_type="endpoint",
                content={"path": f"/user/{i}", "method": "GET"},
                metadata={"summary": f"Get user {i}"},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            temp_db.store_fragment(fragment)
        
        # Query fragments
        query = FragmentQuery(api_id="github", limit=3)
        fragments = temp_db.find_fragments(query)
        
        assert len(fragments) == 3
        assert all(fragment.api_id == "github" for fragment in fragments)
    
    def test_extract_fragments_from_spec(self, temp_db):
        """Test extracting fragments from OpenAPI spec."""
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "description": "Returns a list of users",
                        "operationId": "getUsers",
                        "tags": ["users"]
                    }
                },
                "/users/{id}": {
                    "get": {
                        "summary": "Get user by ID",
                        "operationId": "getUserById",
                        "tags": ["users"]
                    }
                }
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"}
                        },
                        "description": "User object"
                    }
                }
            }
        }
        
        fragments = temp_db.extract_fragments_from_spec("test_api", openapi_spec)
        
        # Should extract 2 endpoints + 1 schema = 3 fragments
        assert len(fragments) == 3
        
        endpoint_fragments = [f for f in fragments if f.fragment_type == "endpoint"]
        schema_fragments = [f for f in fragments if f.fragment_type == "schema"]
        
        assert len(endpoint_fragments) == 2
        assert len(schema_fragments) == 1
        
        # Check endpoint fragments
        endpoint_paths = {f.content["path"] for f in endpoint_fragments}
        assert "/users" in endpoint_paths
        assert "/users/{id}" in endpoint_paths
        
        # Check schema fragment
        schema_names = {f.content["name"] for f in schema_fragments}
        assert "User" in schema_names
    
    def test_find_fragments_by_intent(self, temp_db):
        """Test finding fragments by intent (keyword matching)."""
        # Create fragments with specific keywords
        fragment1 = APIFragment(
            fragment_id="fragment_issue",
            api_id="github",
            fragment_type="endpoint",
            content={"path": "/issues", "method": "GET"},
            metadata={
                "summary": "Get issues",
                "description": "Returns a list of issues",
                "keywords": ["issue", "bug", "problem"]
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        fragment2 = APIFragment(
            fragment_id="fragment_user",
            api_id="github",
            fragment_type="endpoint",
            content={"path": "/user", "method": "GET"},
            metadata={
                "summary": "Get user",
                "description": "Returns user information",
                "keywords": ["user", "profile", "account"]
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        temp_db.store_fragment(fragment1)
        temp_db.store_fragment(fragment2)
        
        # Search for issue-related fragments
        fragments = temp_db.find_fragments_by_intent("github", "I have a bug to report")
        
        assert len(fragments) > 0
        # Should find the issue fragment
        issue_fragments = [f for f in fragments if f.fragment_id == "fragment_issue"]
        assert len(issue_fragments) == 1
    
    def test_cleanup_old_fragments(self, temp_db):
        """Test cleaning up old unused fragments."""
        # Create an old fragment (simulate by setting usage_count = 0)
        old_fragment = APIFragment(
            fragment_id="old_fragment",
            api_id="github",
            fragment_type="endpoint",
            content={"path": "/old", "method": "GET"},
            metadata={"summary": "Old endpoint"},
            created_at=datetime.now() - timedelta(days=31),
            updated_at=datetime.now() - timedelta(days=31),
            usage_count=0
        )
        
        # Create a recently used fragment
        new_fragment = APIFragment(
            fragment_id="new_fragment",
            api_id="github",
            fragment_type="endpoint",
            content={"path": "/new", "method": "GET"},
            metadata={"summary": "New endpoint"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            usage_count=5
        )
        
        temp_db.store_fragment(old_fragment)
        temp_db.store_fragment(new_fragment)
        
        # Clean up fragments older than 30 days
        deleted_count = temp_db.cleanup_old_fragments(days_old=30)
        
        # Should delete the old fragment
        assert deleted_count == 1
        
        # Old fragment should be gone
        assert temp_db.get_fragment("old_fragment") is None
        # New fragment should still exist
        assert temp_db.get_fragment("new_fragment") is not None
    
    def test_get_api_stats(self, temp_db):
        """Test getting API statistics."""
        # Create fragments for an API
        for i in range(3):
            fragment = APIFragment(
                fragment_id=f"fragment_{i}",
                api_id="github",
                fragment_type="endpoint",
                content={"path": f"/endpoint/{i}", "method": "GET"},
                metadata={"summary": f"Endpoint {i}"},
                created_at=datetime.now(),
                updated_at=datetime.now(),
                usage_count=i + 1  # Different usage counts
            )
            temp_db.store_fragment(fragment)
        
        stats = temp_db.get_api_stats("github")
        
        assert stats["api_id"] == "github"
        assert stats["total_fragments"] == 3
        assert "endpoint" in stats["fragment_stats"]
        assert stats["fragment_stats"]["endpoint"] == 3
        assert stats["total_usage"] == 6  # 1 + 2 + 3
        assert stats["average_usage"] == 2.0  # 6 / 3


class TestFragmentBasedOpenAPILLMInterpreter:
    """Tests for FragmentBasedOpenAPILLMInterpreter."""
    
    @pytest.fixture
    def interpreter(self):
        """Create a fragment-based interpreter for testing."""
        return FragmentBasedOpenAPILLMInterpreter()
    
    @pytest.mark.asyncio
    async def test_interpret_intent_with_fragments(self, interpreter):
        """Test interpreting intent with fragments."""
        # Mock the fragment cache
        mock_fragment = APIFragment(
            fragment_id="mock_fragment",
            api_id="github",
            fragment_type="endpoint",
            content={"path": "/issues", "method": "POST"},
            metadata={
                "summary": "Create issue",
                "description": "Create a new issue",
                "keywords": ["issue", "create", "bug"]
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with patch.object(interpreter.fragment_cache, 'find_fragments_by_intent') as mock_find:
            mock_find.return_value = [mock_fragment]
            
            with patch.object(interpreter, '_interpret_with_fragments') as mock_interpret:
                mock_interpret.return_value = FragmentBasedAPICallConfig(
                    endpoint="/issues",
                    method="POST",
                    parameters={"title": "Test issue", "body": "Test description"},
                    description="Create a new issue",
                    fragment_ids=["mock_fragment"],
                    api_id="github",
                    confidence=0.9,
                    reasoning="User wants to create an issue"
                )
                
                # Test interpretation
                config = await interpreter.interpret_intent_with_fragments(
                    user_intent="Create a new bug report",
                    api_id="github"
                )
                
                assert config.endpoint == "/issues"
                assert config.method == "POST"
                assert config.parameters["title"] == "Test issue"
                assert config.api_id == "github"
                assert config.confidence == 0.9
                assert "mock_fragment" in config.fragment_ids
    
    def test_build_fragment_context(self, interpreter):
        """Test building context from fragments."""
        fragments = [
            APIFragment(
                fragment_id="fragment1",
                api_id="github",
                fragment_type="endpoint",
                content={"path": "/issues", "method": "GET"},
                metadata={
                    "summary": "Get issues",
                    "description": "Returns a list of issues",
                    "operation_id": "getIssues",
                    "tags": ["issues"],
                    "keywords": ["issue", "list"]
                },
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            APIFragment(
                fragment_id="fragment2",
                api_id="github",
                fragment_type="schema",
                content={"name": "Issue", "schema": {"type": "object"}},
                metadata={
                    "description": "Issue object",
                    "type": "object",
                    "keywords": ["issue", "object"]
                },
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        
        context = interpreter._build_fragment_context(fragments)
        
        # Should contain endpoint information
        assert "GET /issues" in context
        assert "Get issues" in context
        assert "Returns a list of issues" in context
        
        # Should contain schema information
        assert "Schema: Issue" in context
        assert "Type: object" in context
        assert "Issue object" in context
    
    def test_find_fallback_fragments(self, interpreter):
        """Test finding fallback fragments."""
        with patch.object(interpreter.fragment_cache, 'find_fragments') as mock_find:
            mock_fragment = APIFragment(
                fragment_id="fallback_fragment",
                api_id="github",
                fragment_type="endpoint",
                content={"path": "/user", "method": "GET"},
                metadata={"summary": "Get user"},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            mock_find.return_value = [mock_fragment]
            
            fragments = interpreter._find_fallback_fragments("github")
            
            assert len(fragments) == 1
            assert fragments[0].fragment_id == "fallback_fragment"
            mock_find.assert_called_once_with(FragmentQuery(
                api_id="github",
                fragment_types=['endpoint'],
                limit=10
            ))


if __name__ == "__main__":
    # Run tests
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
