# core/openapi_llm_interpreter.py
from typing import Dict, Any
import json
import logging
from .llm_router import get_llm_for_api_interpretation  # Bestehende LLM-Routing

logger = logging.getLogger(__name__)

class APICallConfig:
    """Konfiguration für einen API-Call"""
    def __init__(self, endpoint: str, method: str, parameters: Dict = None, description: str = ""):
        self.endpoint = endpoint
        self.method = method
        self.parameters = parameters or {}
        self.description = description

class OpenAPILLMInterpreter:
    """Nutzt LLM um OpenAPI Specs zu verstehen und API-Calls zu generieren"""

    def __init__(self):
        self.llm = get_llm_for_api_interpretation()  # Bestehende LLM-Instanz

    def interpret_intent(self, user_intent: str, openapi_spec: Dict = None, **kwargs) -> APICallConfig:
        """Interpretiert User-Intent und erstellt API-Call-Konfiguration"""

        # OpenAPI-Pfade extrahieren oder Fallback für universelle APIs
        if openapi_spec:
            paths = openapi_spec.get('paths', {})
            paths_info = json.dumps(paths, indent=2)
        else:
            # Fallback für universelle APIs ohne OpenAPI Spec
            paths_info = """
            COMMON ENDPOINTS:
            - /user, /users (GET) - User information
            - /repos, /repositories (GET/POST) - Repository operations
            - /issues (GET/POST) - Issue management
            - /messages, /chat (POST) - Messaging
            - /files (GET/POST) - File operations
            """

        prompt = f"""
Du bist ein API-Experte. Analysiere die User-Anfrage und die verfügbaren API-Endpunkte.
Finde den passendsten Endpunkt für die Anfrage.

USER INTENT: "{user_intent}"

VERFÜGBARE ENDPOINTS:
{paths_info}

ZUSÄTZLICHE PARAMETER: {json.dumps(kwargs) if kwargs else 'Keine'}

Antworte MIT EINEM JSON-Objekt im folgenden Format:
{{
  "endpoint": "/user/repos",
  "method": "POST",
  "parameters": {{"name": "my-repo", "private": true}},
  "confidence": 0.95,
  "reasoning": "Kurze Erklärung warum dieser Endpoint passt"
}}

WICHTIG:
- Verwende plausible Endpoints basierend auf dem Intent
- Setze plausible Parameter basierend auf dem Intent
- Gib eine confidence zwischen 0-1 an
"""

        try:
            llm_response = self.llm.generate(prompt)
            parsed_response = self._parse_llm_response(llm_response)

            if parsed_response['confidence'] < 0.7:
                logger.warning(f"⚠️ Niedrige Confidence für Intent: {user_intent}")

            return APICallConfig(
                endpoint=parsed_response['endpoint'],
                method=parsed_response['method'],
                parameters=parsed_response['parameters'],
                description=parsed_response.get('reasoning', '')
            )

        except Exception as e:
            logger.error(f"❌ LLM Interpretation fehlgeschlagen: {e}")
            return APICallConfig("/", "GET", {}, "Fallback bei Fehler")

    def _parse_llm_response(self, response: str) -> Dict:
        """Parst LLM-Response als JSON"""
        try:
            # JSON aus Response extrahieren (LLM könnte extra Text hinzufügen)
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                raise ValueError("Kein JSON in Response gefunden")
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON Parse Fehler: {e}")
            return {
                "endpoint": "/",
                "method": "GET",
                "parameters": {},
                "confidence": 0.0,
                "reasoning": "JSON Parse Fehler"
            }