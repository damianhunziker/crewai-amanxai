"""
Enhanced OpenAPI LLM Interpreter with Fragment-Based Lazy Loading

This module extends the OpenAPILLMInterpreter to support lazy loading of API fragments
instead of loading entire OpenAPI specifications.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .openapi_llm_interpreter import OpenAPILLMInterpreter, APICallConfig
from .api_fragment_cache import APIFragment, FragmentQuery, fragment_cache
from .llm_router import get_llm_for_api_interpretation

logger = logging.getLogger(__name__)


class FragmentBasedAPICallConfig(APICallConfig):
    """Extended API call configuration with fragment metadata."""
    def __init__(self, endpoint: str, method: str, parameters: Dict = None, description: str = "",
                 fragment_ids: List[str] = None, api_id: str = "", confidence: float = 0.0, reasoning: str = ""):
        super().__init__(endpoint, method, parameters, description)
        self.fragment_ids = fragment_ids or []
        self.api_id = api_id
        self.confidence = confidence
        self.reasoning = reasoning


class FragmentBasedOpenAPILLMInterpreter(OpenAPILLMInterpreter):
    """
    LLM interpreter that uses fragment-based lazy loading of OpenAPI specifications.
    
    Instead of loading entire OpenAPI specs, this interpreter:
    1. Loads only relevant fragments based on user intent
    2. Uses semantic search to find matching fragments
    3. Combines fragments for LLM context
    4. Updates fragment usage statistics
    """
    
    def __init__(self):
        super().__init__()
        self.fragment_cache = fragment_cache
        logger.info("✅ Fragment-based OpenAPI LLM interpreter initialized")
    
    async def interpret_intent_with_fragments(
        self, 
        user_intent: str, 
        api_id: str,
        openapi_spec: Optional[Dict] = None,
        **kwargs
    ) -> FragmentBasedAPICallConfig:
        """
        Interpret user intent using fragment-based lazy loading.
        
        Args:
            user_intent: Natural language user request
            api_id: Identifier for the API (e.g., 'github', 'notion')
            openapi_spec: Optional full OpenAPI spec (for initial population)
            **kwargs: Additional parameters
            
        Returns:
            FragmentBasedAPICallConfig with fragment metadata
        """
        # Step 1: Extract fragments from spec if provided (initial population)
        if openapi_spec:
            await self._populate_fragments_from_spec(api_id, openapi_spec)
        
        # Step 2: Find relevant fragments based on intent
        relevant_fragments = self.fragment_cache.find_fragments_by_intent(api_id, user_intent)
        
        # Step 3: If no fragments found, try broader search
        if not relevant_fragments:
            logger.warning(f"⚠️ No fragments found for intent: {user_intent}")
            relevant_fragments = self._find_fallback_fragments(api_id)
        
        # Step 4: Build context from fragments
        fragment_context = self._build_fragment_context(relevant_fragments)
        
        # Step 5: Use LLM to interpret intent with fragment context
        return await self._interpret_with_fragments(
            user_intent, api_id, fragment_context, relevant_fragments, **kwargs
        )
    
    async def _populate_fragments_from_spec(self, api_id: str, openapi_spec: Dict[str, Any]):
        """Extract and store fragments from a full OpenAPI specification."""
        try:
            fragments = self.fragment_cache.extract_fragments_from_spec(api_id, openapi_spec)
            
            for fragment in fragments:
                self.fragment_cache.store_fragment(fragment)
            
            logger.info(f"✅ Populated {len(fragments)} fragments for API: {api_id}")
            
        except Exception as e:
            logger.error(f"❌ Error populating fragments for {api_id}: {e}")
    
    def _find_fallback_fragments(self, api_id: str) -> List[APIFragment]:
        """Find fallback fragments when intent-based search fails."""
        query = FragmentQuery(
            api_id=api_id,
            fragment_types=['endpoint'],
            limit=10
        )
        return self.fragment_cache.find_fragments(query)
    
    def _build_fragment_context(self, fragments: List[APIFragment]) -> str:
        """Build LLM context string from fragments."""
        if not fragments:
            return "No API fragments available."
        
        context_parts = []
        
        for fragment in fragments:
            if fragment.fragment_type == 'endpoint':
                content = fragment.content
                metadata = fragment.metadata
                
                endpoint_info = f"""
Endpoint: {content.get('method', 'GET')} {content.get('path', '')}
Summary: {metadata.get('summary', 'No summary')}
Description: {metadata.get('description', 'No description')}
Operation ID: {metadata.get('operation_id', '')}
Tags: {', '.join(metadata.get('tags', []))}
Keywords: {', '.join(metadata.get('keywords', []))}
"""
                context_parts.append(endpoint_info)
            
            elif fragment.fragment_type == 'schema':
                content = fragment.content
                metadata = fragment.metadata
                
                schema_info = f"""
Schema: {content.get('name', '')}
Type: {metadata.get('type', 'object')}
Description: {metadata.get('description', 'No description')}
"""
                context_parts.append(schema_info)
        
        return "\n---\n".join(context_parts)
    
    async def _interpret_with_fragments(
        self,
        user_intent: str,
        api_id: str,
        fragment_context: str,
        fragments: List[APIFragment],
        **kwargs
    ) -> FragmentBasedAPICallConfig:
        """Use heuristic or LLM to interpret intent with fragment context."""
        
        # Build prompt for LLM
        prompt = f"""
Du bist ein API-Experte. Analysiere die User-Anfrage und die verfügbaren API-Fragmente.
Finde den passendsten Endpunkt für die Anfrage.

USER INTENT: "{user_intent}"

API ID: {api_id}

VERFÜGBARE API-FRAGMENTE (nur relevante Teile geladen):
{fragment_context}

ZUSÄTZLICHE PARAMETER: {json.dumps(kwargs) if kwargs else 'Keine'}

WICHTIG: Du arbeitest mit Fragmenten, nicht mit der vollständigen API-Spezifikation.
Wähle den besten Endpunkt basierend auf den verfügbaren Fragmenten.

Antworte MIT EINEM JSON-Objekt im folgenden Format:
{{
  "endpoint": "/user/repos",
  "method": "POST",
  "parameters": {{"name": "my-repo", "private": true}},
  "confidence": 0.95,
  "reasoning": "Kurze Erklärung warum dieser Endpoint passt",
  "fragment_ids": ["fragment_id_1", "fragment_id_2"]
}}

Regeln:
1. Verwende nur Endpoints die in den Fragmenten vorkommen
2. Setze plausible Parameter basierend auf dem Intent
3. Gib eine confidence zwischen 0-1 an
4. Liste die fragment_ids der verwendeten Fragmente
"""
        
        # Try LLM interpretation first
        try:
            # Check if LLM has invoke method (CrewAI LLM interface)
            if hasattr(self.llm, 'invoke'):
                llm_response = self.llm.invoke(prompt)
            elif hasattr(self.llm, 'generate'):
                llm_response = self.llm.generate(prompt)
            else:
                # Try to call it directly
                llm_response = self.llm(prompt)
            
            parsed_response = self._parse_llm_response(llm_response)
            
            # Extract fragment IDs from used fragments
            fragment_ids = [fragment.fragment_id for fragment in fragments]
            
            if parsed_response['confidence'] < 0.7:
                logger.warning(f"⚠️ Niedrige Confidence für Intent: {user_intent}")
            
            return FragmentBasedAPICallConfig(
                endpoint=parsed_response['endpoint'],
                method=parsed_response['method'],
                parameters=parsed_response['parameters'],
                description=parsed_response.get('reasoning', ''),
                fragment_ids=fragment_ids,
                api_id=api_id,
                confidence=parsed_response['confidence'],
                reasoning=parsed_response.get('reasoning', '')
            )
            
        except Exception as e:
            logger.warning(f"⚠️ LLM interpretation failed, using heuristic: {e}")
            # Fallback to heuristic-based interpretation
            return self._heuristic_interpretation(
                user_intent, api_id, fragments, **kwargs
            )
    
    def _heuristic_interpretation(
        self,
        user_intent: str,
        api_id: str,
        fragments: List[APIFragment],
        **kwargs
    ) -> FragmentBasedAPICallConfig:
        """Heuristic-based interpretation when LLM is not available."""
        
        # Simple keyword matching
        intent_lower = user_intent.lower()
        fragment_ids = [fragment.fragment_id for fragment in fragments]
        
        # Default fallback
        default_config = FragmentBasedAPICallConfig(
            endpoint="/",
            method="GET",
            parameters={},
            description="Heuristic fallback",
            fragment_ids=fragment_ids,
            api_id=api_id,
            confidence=0.3,
            reasoning="Using heuristic matching due to LLM unavailability"
        )
        
        if not fragments:
            return default_config
        
        # Try to find the most relevant fragment
        best_fragment = None
        best_score = 0
        
        for fragment in fragments:
            if fragment.fragment_type == 'endpoint':
                score = self._calculate_relevance_score(fragment, intent_lower)
                if score > best_score:
                    best_score = score
                    best_fragment = fragment
        
        if best_fragment and best_score > 0.1:
            content = best_fragment.content
            metadata = best_fragment.metadata
            
            # Extract parameters from kwargs
            parameters = {}
            if 'owner' in kwargs:
                parameters['owner'] = kwargs['owner']
            if 'repo' in kwargs:
                parameters['repo'] = kwargs['repo']
            
            return FragmentBasedAPICallConfig(
                endpoint=content.get('path', '/'),
                method=content.get('method', 'GET'),
                parameters=parameters,
                description=metadata.get('summary', ''),
                fragment_ids=fragment_ids,
                api_id=api_id,
                confidence=min(best_score, 0.8),  # Cap confidence
                reasoning=f"Heuristic match based on keywords: {metadata.get('keywords', [])}"
            )
        
        return default_config
    
    def _calculate_relevance_score(self, fragment: APIFragment, intent_lower: str) -> float:
        """Calculate relevance score between fragment and intent."""
        score = 0.0
        
        # Check metadata keywords
        keywords = fragment.metadata.get('keywords', [])
        for keyword in keywords:
            if keyword.lower() in intent_lower:
                score += 0.2
        
        # Check summary and description
        summary = fragment.metadata.get('summary', '').lower()
        description = fragment.metadata.get('description', '').lower()
        
        for word in intent_lower.split():
            if len(word) > 3:  # Only meaningful words
                if word in summary:
                    score += 0.1
                if word in description:
                    score += 0.05
        
        # Check fragment type
        if fragment.fragment_type == 'endpoint':
            content = fragment.content
            path = content.get('path', '').lower()
            method = content.get('method', '').lower()
            
            # Common intent patterns
            if 'create' in intent_lower or 'add' in intent_lower or 'post' in intent_lower:
                if method == 'post':
                    score += 0.3
            elif 'get' in intent_lower or 'fetch' in intent_lower or 'read' in intent_lower:
                if method == 'get':
                    score += 0.3
            elif 'update' in intent_lower or 'modify' in intent_lower or 'put' in intent_lower:
                if method in ['put', 'patch']:
                    score += 0.3
            elif 'delete' in intent_lower or 'remove' in intent_lower:
                if method == 'delete':
                    score += 0.3
        
        return min(score, 1.0)  # Cap at 1.0
    
    def get_api_stats(self, api_id: str) -> Dict[str, Any]:
        """Get statistics for an API including fragment usage."""
        return self.fragment_cache.get_api_stats(api_id)
    
    def cleanup_old_fragments(self, days_old: int = 30) -> int:
        """Clean up old unused fragments."""
        return self.fragment_cache.cleanup_old_fragments(days_old)


# Singleton instance for easy access
fragment_interpreter = FragmentBasedOpenAPILLMInterpreter()
