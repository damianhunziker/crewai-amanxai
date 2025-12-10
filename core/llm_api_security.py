# core/llm_api_security.py
from typing import Dict, Any, List
import logging
import re

logger = logging.getLogger(__name__)

class LLMapiSecurity:
    """Sicherheitsvalidierung für LLM-generierte API-Calls"""

    def __init__(self):
        self.dangerous_patterns = [
            r'<script',  # XSS
            r'union.*select',  # SQL Injection
            r';\s*rm\s+',  # Command Injection
            r'\.\./',  # Path Traversal
        ]
        self.rate_limits = {}  # api_id -> call_count

    def validate_api_call(self, api_call_config: Dict, openapi_spec: Dict = None) -> bool:
        """Validiert einen API-Call vor Ausführung"""

        # 1. HTTP-Methode ist erlaubt
        allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        if api_call_config.get('method', '').upper() not in allowed_methods:
            logger.warning(f"❌ Nicht erlaubte HTTP-Methode: {api_call_config.get('method')}")
            return False

        # 2. Parameter-Sanitization
        if not self._sanitize_parameters(api_call_config.get('parameters', {})):
            logger.warning("❌ Unsichere Parameter erkannt")
            return False

        # 3. Rate Limiting prüfen
        if not self._check_rate_limit(api_call_config.get('api_id', 'unknown')):
            logger.warning("❌ Rate Limit überschritten")
            return False

        # 4. Endpoint existiert in OpenAPI Spec (falls verfügbar)
        if openapi_spec and not self._endpoint_exists(api_call_config.get('endpoint', ''), openapi_spec):
            logger.warning(f"❌ Endpoint nicht in Spec gefunden: {api_call_config.get('endpoint')}")
            return False

        return True

    def _endpoint_exists(self, endpoint: str, openapi_spec: Dict) -> bool:
        """Prüft ob Endpoint in OpenAPI Spec existiert"""
        paths = openapi_spec.get('paths', {})
        return endpoint in paths

    def _sanitize_parameters(self, parameters: Dict) -> bool:
        """Sanitisiert Parameter und prüft auf gefährliche Inhalte"""
        for key, value in parameters.items():
            if isinstance(value, str):
                # Prüfe auf gefährliche Patterns
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        logger.warning(f"❌ Gefährliches Pattern in Parameter {key}: {pattern}")
                        return False

                # Längen-Limit
                if len(value) > 10000:
                    logger.warning(f"❌ Parameter {key} zu lang: {len(value)} Zeichen")
                    return False

        return True

    def _check_rate_limit(self, api_id: str, limit: int = 100) -> bool:
        """Prüft Rate Limiting pro API"""
        if api_id not in self.rate_limits:
            self.rate_limits[api_id] = 0

        self.rate_limits[api_id] += 1

        if self.rate_limits[api_id] > limit:
            return False

        return True

    def reset_rate_limits(self):
        """Reset rate limits (z.B. täglich)"""
        self.rate_limits.clear()
        logger.info("🔄 Rate limits zurückgesetzt")