"""
Fragment-Based API Tool for CrewAI Agents.

This tool allows agents to use fragment-based lazy loading for OpenAPI specifications,
enabling autonomous API research without loading entire specs.
"""

import json
import logging
from typing import Dict, Any, Optional, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .openapi_llm_interpreter_fragment import fragment_interpreter
from .api_fragment_cache import fragment_cache

logger = logging.getLogger(__name__)


class FragmentBasedAPIToolSchema(BaseModel):
    """Schema for fragment-based API tool."""
    user_intent: str = Field(description="Natural language description of what the user wants to do")
    api_id: str = Field(description="Identifier for the API (e.g., 'github', 'notion', 'slack')")
    openapi_spec: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional OpenAPI specification JSON for initial population"
    )
    additional_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional parameters for the API call"
    )


class FragmentBasedAPITool(BaseTool):
    """
    Tool for agents to use fragment-based lazy loading of OpenAPI specifications.
    
    This tool enables agents to:
    1. Research APIs autonomously using fragment cache
    2. Load only relevant parts of API specs
    3. Construct API calls from fragments
    4. Update fragment usage statistics
    """
    
    name: str = "fragment_based_api_research"
    description: str = """
    Research and use APIs autonomously using fragment-based lazy loading.
    Instead of loading entire OpenAPI specifications, this tool loads only relevant
    fragments based on user intent. Perfect for exploring unknown APIs or
    researching API capabilities.
    
    Examples:
    - "I want to create a GitHub issue"
    - "How can I get user information from the Notion API?"
    - "What endpoints are available for creating Slack messages?"
    """
    args_schema: Type[BaseModel] = FragmentBasedAPIToolSchema
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._interpreter = fragment_interpreter
        self._cache = fragment_cache
        logger.info("✅ Fragment-based API tool initialized")
    
    @property
    def interpreter(self):
        return self._interpreter
    
    @property
    def cache(self):
        return self._cache
    
    def _run(
        self,
        user_intent: str,
        api_id: str,
        openapi_spec: Optional[Dict[str, Any]] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Research API using fragment-based lazy loading.
        
        Args:
            user_intent: Natural language description of what the user wants
            api_id: Identifier for the API
            openapi_spec: Optional OpenAPI specification for initial population
            additional_params: Additional parameters for the API call
            
        Returns:
            String with research results and API call configuration
        """
        try:
            # Convert to async call
            import asyncio
            
            async def async_run():
                return await self.interpreter.interpret_intent_with_fragments(
                    user_intent=user_intent,
                    api_id=api_id,
                    openapi_spec=openapi_spec,
                    **(additional_params or {})
                )
            
            # Run async function
            config = asyncio.run(async_run())
            
            # Get API statistics
            stats = self.cache.get_api_stats(api_id)
            
            # Format response
            response = self._format_response(config, stats)
            
            logger.info(f"✅ Fragment-based research completed for {api_id}")
            return response
            
        except Exception as e:
            error_msg = f"❌ Fragment-based API research failed: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _format_response(self, config, stats) -> str:
        """Format the response for the agent."""
        
        # Basic API call info
        response_parts = [
            "🔍 **API Research Results**",
            f"**API ID**: {config.api_id}",
            f"**Confidence**: {config.confidence:.2%}",
            f"**Reasoning**: {config.reasoning}",
            "",
            "🚀 **Recommended API Call**",
            f"**Endpoint**: {config.method} {config.endpoint}",
            f"**Parameters**: {json.dumps(config.parameters, indent=2)}",
            f"**Description**: {config.description}",
        ]
        
        # Fragment information
        if config.fragment_ids:
            response_parts.extend([
                "",
                "🧩 **Used Fragments**",
                f"Loaded {len(config.fragment_ids)} relevant fragments"
            ])
            
            # Get fragment details
            fragments = []
            for fragment_id in config.fragment_ids[:3]:  # Show first 3
                fragment = self.cache.get_fragment(fragment_id)
                if fragment:
                    if fragment.fragment_type == 'endpoint':
                        fragments.append(f"- {fragment.content.get('method', 'GET')} {fragment.content.get('path', '')}: {fragment.metadata.get('summary', '')}")
                    else:
                        fragments.append(f"- Schema: {fragment.content.get('name', '')}")
            
            if fragments:
                response_parts.append("\n".join(fragments))
        
        # API statistics
        response_parts.extend([
            "",
            "📊 **API Statistics**",
            f"**Total fragments**: {stats.get('total_fragments', 0)}",
            f"**Fragment types**: {json.dumps(stats.get('fragment_stats', {}), indent=2)}",
            f"**Total usage**: {stats.get('total_usage', 0)}",
            f"**Average usage**: {stats.get('average_usage', 0):.2f}",
        ])
        
        # Recommendations
        response_parts.extend([
            "",
            "💡 **Recommendations**",
            "1. Use the recommended API call above",
            "2. If confidence is low, provide more specific intent",
            "3. Consider adding more fragments to the cache",
            "4. Monitor fragment usage for optimization",
        ])
        
        return "\n".join(response_parts)
    
    def get_api_fragments(self, api_id: str, limit: int = 10) -> str:
        """
        Get available fragments for an API.
        
        Args:
            api_id: API identifier
            limit: Maximum number of fragments to return
            
        Returns:
            String with fragment information
        """
        try:
            from .api_fragment_cache import FragmentQuery
            
            query = FragmentQuery(api_id=api_id, limit=limit)
            fragments = self.cache.find_fragments(query)
            
            if not fragments:
                return f"No fragments found for API: {api_id}"
            
            response_parts = [
                f"📚 **Available Fragments for {api_id}**",
                f"Found {len(fragments)} fragments",
                ""
            ]
            
            for i, fragment in enumerate(fragments, 1):
                if fragment.fragment_type == 'endpoint':
                    response_parts.append(
                        f"{i}. **Endpoint**: {fragment.content.get('method', 'GET')} {fragment.content.get('path', '')}"
                    )
                    response_parts.append(f"   Summary: {fragment.metadata.get('summary', 'No summary')}")
                    response_parts.append(f"   Usage: {fragment.usage_count} times")
                else:
                    response_parts.append(
                        f"{i}. **Schema**: {fragment.content.get('name', 'Unknown')}"
                    )
                    response_parts.append(f"   Type: {fragment.metadata.get('type', 'object')}")
                    response_parts.append(f"   Description: {fragment.metadata.get('description', 'No description')}")
                
                response_parts.append("")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            return f"Error getting fragments: {str(e)}"
    
    def cleanup_fragments(self, days_old: int = 30) -> str:
        """
        Clean up old unused fragments.
        
        Args:
            days_old: Remove fragments older than this many days
            
        Returns:
            Cleanup results
        """
        try:
            deleted_count = self.cache.cleanup_old_fragments(days_old)
            return f"🧹 Cleaned up {deleted_count} old fragments (older than {days_old} days)"
        except Exception as e:
            return f"Error cleaning fragments: {str(e)}"


# Factory function for easy access
def get_fragment_based_api_tool() -> FragmentBasedAPITool:
    """Get a fragment-based API tool instance."""
    return FragmentBasedAPITool()
