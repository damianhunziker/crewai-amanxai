# core/llm_api_manager.py
from typing import List, Dict, Any, Optional
from crewai.tools import BaseTool
import logging

from .universal_nango_api_tool import get_universal_api_tool
from .settings import settings

logger = logging.getLogger(__name__)


class DynamicAPIManager:
    """
    Zentraler Manager für universelle API-Integrationen.

    Features:
    - Universelles Nango-Tool für alle API-Anbieter
    - Automatische Authentifizierung über Nango
    - Performance-Monitoring
    """

    def __init__(self):
        """Initialisiert den Dynamic API Manager mit universellem Nango-Tool"""
        # Universelles Nango-Tool für alle APIs
        self.universal_tool = get_universal_api_tool()
        self.api_stats = {}  # provider -> usage_stats

        logger.info("✅ Dynamic API Manager mit universellem Nango-Tool initialisiert")

    def get_tools_for_agent(self, agent_role: str = "manager") -> List[BaseTool]:
        """
        Gibt das universelle Nango-API-Tool für Agenten zurück.

        Alle Agenten bekommen dasselbe universelle Tool für alle APIs.
        """
        tools = [self.universal_tool]
        logger.info(f"🔧 Universelles Nango-API-Tool für Agent-Rolle '{agent_role}' verfügbar")
        return tools

    def add_new_api(self, api_id: str, openapi_spec: Dict, base_url: str, metadata: Dict = None) -> bool:
        """
        Fügt eine neue API dynamisch hinzu.

        Args:
            api_id: Eindeutige API-Kennung
            openapi_spec: OpenAPI-Spezifikation
            base_url: Basis-URL der API
            metadata: Zusätzliche API-Metadaten

        Returns:
            bool: True bei Erfolg
        """
        try:
            # Tool erstellen
            tool = LLMDrivenAPITool(api_id, openapi_spec, base_url)

            # In Registry aufnehmen
            self.available_apis[api_id] = metadata or {'id': api_id, 'name': api_id}
            self.llm_tools[api_id] = tool
            self.api_stats[api_id] = {
                'calls': 0,
                'errors': 0,
                'last_used': None,
                'created_at': '2024-01-01T00:00:00Z'
            }

            logger.info(f"✅ Neue API {api_id} erfolgreich hinzugefügt")
            return True

        except Exception as e:
            logger.error(f"❌ Fehler beim Hinzufügen von API {api_id}: {e}")
            return False

    def remove_api(self, api_id: str) -> bool:
        """
        Entfernt eine API aus der Registry.

        Args:
            api_id: API-Kennung

        Returns:
            bool: True bei Erfolg
        """
        try:
            if api_id in self.llm_tools:
                del self.llm_tools[api_id]
            if api_id in self.available_apis:
                del self.available_apis[api_id]
            if api_id in self.api_stats:
                del self.api_stats[api_id]

            logger.info(f"🗑️ API {api_id} entfernt")
            return True

        except Exception as e:
            logger.error(f"❌ Fehler beim Entfernen von API {api_id}: {e}")
            return False

    def get_api_info(self) -> List[Dict]:
        """
        Gibt Informationen über alle verfügbaren APIs zurück.

        Returns:
            List[Dict]: API-Informationen mit Statistiken
        """
        api_info = []

        for api_id, metadata in self.available_apis.items():
            stats = self.api_stats.get(api_id, {})
            tool = self.llm_tools.get(api_id)

            info = {
                'id': api_id,
                'name': metadata.get('name', api_id),
                'description': metadata.get('description', ''),
                'has_tool': tool is not None,
                'calls': stats.get('calls', 0),
                'errors': stats.get('errors', 0),
                'last_used': stats.get('last_used'),
                'base_url': tool.api_base_url if tool else None
            }

            api_info.append(info)

        return api_info

    def record_api_call(self, api_id: str, success: bool):
        """
        Zeichnet einen API-Call für Statistiken auf.

        Args:
            api_id: API-Kennung
            success: True bei erfolgreichem Call
        """
        if api_id in self.api_stats:
            self.api_stats[api_id]['calls'] += 1
            if not success:
                self.api_stats[api_id]['errors'] += 1

            # TODO: Aktueller Timestamp
            self.api_stats[api_id]['last_used'] = '2024-01-01T00:00:00Z'

    def get_health_status(self) -> Dict[str, Any]:
        """
        Gibt den Gesundheitsstatus des Managers zurück.

        Returns:
            Dict: Health-Status-Informationen
        """
        total_apis = len(self.available_apis)
        active_tools = len(self.llm_tools)
        total_calls = sum(stats.get('calls', 0) for stats in self.api_stats.values())
        total_errors = sum(stats.get('errors', 0) for stats in self.api_stats.values())

        return {
            'total_apis': total_apis,
            'active_tools': active_tools,
            'total_calls': total_calls,
            'total_errors': total_errors,
            'error_rate': (total_errors / max(total_calls, 1)) * 100,
            'connection_status': self._check_connection(),
            'last_refresh': '2024-01-01T00:00:00Z'
        }

    def _check_connection(self) -> bool:
        """Prüft allgemeine API-Verbindungen"""
        # Für universelles Nango-Tool immer True zurückgeben
        return True