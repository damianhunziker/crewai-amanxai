# core/llm_driven_api_tool.py
from typing import Dict, Any, Optional
from crewai.tools import BaseTool
import json
import logging
import requests

from .openapi_llm_interpreter import OpenAPILLMInterpreter
from .llm_api_security import LLMapiSecurity
from .settings import settings

logger = logging.getLogger(__name__)

class LLMDrivenAPITool(BaseTool):
    """LLM-gesteuertes Tool für dynamische API-Calls basierend auf OpenAPI Specs"""

    def __init__(self, api_id: str, openapi_spec: Dict, api_base_url: str):
        super().__init__()
        self.api_id = api_id
        self.openapi_spec = openapi_spec
        self.api_base_url = api_base_url
        self.llm_interpreter = OpenAPILLMInterpreter()
        self.security_manager = LLMapiSecurity()

    @property
    def name(self) -> str:
        return f"llm_api_tool_{self.api_id}"

    @property
    def description(self) -> str:
        return f"LLM-gesteuerter Zugriff auf {self.api_id} API"

    def _run(self, user_intent: str, **kwargs) -> str:
        """Führt LLM-gesteuerten API-Call aus"""
        try:
            logger.info(f"🔄 Processing intent for {self.api_id}: {user_intent}")

            # 1. LLM interpretiert Intent basierend auf OpenAPI Spec
            api_call_config = self.llm_interpreter.interpret_intent(
                user_intent, self.openapi_spec, **kwargs
            )

            # 2. Sicherheitsvalidierung
            api_call_dict = {
                'endpoint': api_call_config.endpoint,
                'method': api_call_config.method,
                'parameters': api_call_config.parameters,
                'api_id': self.api_id
            }

            if not self.security_manager.validate_api_call(api_call_dict, self.openapi_spec):
                return "❌ API-Call wurde aus Sicherheitsgründen blockiert"

            # 3. Authentifizierung (vereinfacht - würde normalerweise über Bitwarden gehen)
            auth_token = self._get_auth_token()

            # 4. API-Call ausführen
            result = self._execute_api_call(api_call_dict, auth_token)

            logger.info(f"✅ API-Call erfolgreich für {self.api_id}")
            return result

        except Exception as e:
            logger.error(f"❌ LLM API Tool Fehler für {self.api_id}: {e}")
            return f"❌ Fehler bei API-Call: {str(e)}"

    def _get_auth_token(self) -> Optional[str]:
        """Holt Authentifizierungstoken (vereinfacht)"""
        # In der echten Implementierung würde dies über Bitwarden/Apidog gehen
        # Für Demo-Zwecke verwenden wir eine Dummy-Implementierung
        auth_tokens = {
            'github': 'ghp_dummy_token_for_github',
            'notion': 'secret_dummy_notion_token',
            'openai': 'sk-dummy-openai-key'
        }
        return auth_tokens.get(self.api_id)

    def _execute_api_call(self, call_config: Dict, auth_token: str) -> str:
        """Führt den tatsächlichen API-Call aus"""
        url = f"{self.api_base_url}{call_config['endpoint']}"
        method = call_config.get('method', 'GET').upper()
        params = call_config.get('parameters', {})

        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }

        # API-Key Header für manche APIs
        if self.api_id in ['openai']:
            headers['Authorization'] = f'Bearer {auth_token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=settings.apidog_timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=params, timeout=settings.apidog_timeout)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=params, timeout=settings.apidog_timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=settings.apidog_timeout)
            else:
                return f"❌ Nicht unterstützte HTTP-Methode: {method}"

            response.raise_for_status()

            # Response formatieren
            if response.content:
                try:
                    return json.dumps(response.json(), indent=2)
                except json.JSONDecodeError:
                    return response.text
            else:
                return "✅ Operation erfolgreich"

        except requests.exceptions.HTTPError as e:
            return f"❌ HTTP-Fehler: {response.status_code} - {response.text}"
        except Exception as e:
            return f"❌ API-Fehler: {str(e)}"