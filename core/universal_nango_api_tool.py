"""
Universelles API Tool

Ein zentrales Tool für alle API-Integrationen über Tyk.
Agenten können jede API verwenden ohne spezifische Tools pro Provider.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict
from crewai.tools import BaseTool

from .settings import settings

logger = logging.getLogger(__name__)


class UniversalAPIToolSchema(BaseModel):
    """Schema für das universelle API Tool"""
    provider: str = Field(..., description="API-Provider (z.B. 'github', 'notion', 'slack', 'openai')")
    endpoint: str = Field(..., description="API-Endpoint ohne Base-URL (z.B. '/repos', '/users', '/databases')")
    method: str = Field(default="GET", description="HTTP-Methode (GET, POST, PUT, DELETE, PATCH)")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Request-Parameter (JSON-Body für POST/PUT, Query-Params für GET)")
    description: Optional[str] = Field(default=None, description="Optionale Beschreibung des API-Calls")


class UniversalAPITool(BaseTool):
    """
    Universelles API-Tool für alle Tyk-Integrationen.

    Dieses Tool ermöglicht Agenten, jede API über Tyk anzusprechen,
    ohne dass spezifische Tools pro Provider nötig sind.

    Verwendung:
    - provider: API-Provider (github, notion, slack, etc.)
    - endpoint: API-Endpoint (z.B. '/repos', '/users')
    - method: HTTP-Methode
    - params: Request-Daten
    """

    name: str = "universal_api_tool"
    description: str = "Universelles API-Tool für alle Tyk-Integrationen. Kann jede API über Tyk ansprechen."
    args_schema: type[BaseModel] = UniversalAPIToolSchema

    model_config = ConfigDict(validate_assignment=False, extra='allow')

    def __init__(self):
        """Initialisiert das universelle API Tool"""
        super().__init__()

        # Tyk Gateway URL
        self.tyk_url = settings.tyk_base_url

        # Provider-Mapping für bessere User-Experience
        self.provider_aliases = {}
        # Mapping von api_id zu listen_path
        self.provider_listen_paths = {}
        
        # Dynamisch verfügbare APIs von Tyk laden
        self._load_tyk_apis()
        
        # Fallback für bekannte Provider, falls Tyk nicht erreichbar
        if not self.provider_aliases:
            self.provider_aliases = self._get_fallback_aliases()
            logger.warning("Tyk API nicht erreichbar, verwende Fallback-Aliases")
        else:
            logger.info(f"✅ Dynamisch {len(self.provider_aliases)} Provider von Tyk geladen")

    def _load_tyk_apis(self):
        """Lädt verfügbare APIs von Tyk Gateway"""
        try:
            import requests
            tyk_admin_url = self.tyk_url.replace('://', '://admin.')
            # Alternativ: Tyk Admin API auf Port 8080 mit Admin-Key
            # Verwende den bekannten Admin-Key
            headers = {'x-tyk-authorization': '97158e409154e3fe7c3d5b4e9afbb1e9'}
            response = requests.get(f"{self.tyk_url}/tyk/apis", headers=headers, timeout=5)
            if response.status_code == 200:
                apis = response.json()
                for api in apis:
                    api_id = api.get('api_id')
                    name = api.get('name', '').lower()
                    slug = api.get('slug', '')
                    listen_path = api.get('proxy', {}).get('listen_path', '')
                    if api_id:
                        # Primärer Alias ist der api_id
                        self.provider_aliases[api_id] = api_id
                        # Zusätzliche Aliases basierend auf Name und Slug
                        if name:
                            self.provider_aliases[name] = api_id
                        if slug:
                            self.provider_aliases[slug] = api_id
                        # Extrahiere Basisnamen aus api_id (z.B. 'wordpress' aus 'wordpress-proxy-2')
                        # Einfache Logik: Nimm den Teil vor dem ersten '-'
                        if '-' in api_id:
                            base_id = api_id.split('-')[0]
                            if base_id and base_id != api_id:
                                self.provider_aliases[base_id] = api_id
                                # Auch ohne Bindestrich
                                self.provider_aliases[base_id.replace('-', '')] = api_id
                        # Speichere listen_path
                        if listen_path:
                            # Normalisiere listen_path (entferne führende/trailing Slashes)
                            listen_path = listen_path.rstrip('/')
                            self.provider_listen_paths[api_id] = listen_path
                logger.info(f"Geladene APIs von Tyk: {list(set(self.provider_aliases.values()))}")
                logger.debug(f"Aliases: {self.provider_aliases}")
                logger.debug(f"Listen paths: {self.provider_listen_paths}")
            else:
                logger.warning(f"Tyk API Response {response.status_code}: {response.text}")
        except Exception as e:
            logger.warning(f"Konnte Tyk APIs nicht laden: {e}")

    def _get_fallback_aliases(self):
        """Fallback-Aliases für bekannte Provider"""
        return {
            # GitHub (inkl. PAT)
            'gh': 'github',
            'git': 'github',
            'github': 'github',
            'github-pat': 'github',
            'ghpat': 'github',
            # Notion
            'notion': 'notion',
            'note': 'notion',
            # Slack
            'slack': 'slack',
            'chat': 'slack',
            # OpenAI
            'openai': 'openai',
            'ai': 'openai',
            'gpt': 'openai',
            # Discord
            'discord': 'discord',
            # Figma
            'figma': 'figma',
            'design': 'figma',
            # Google Services
            'dropbox': 'dropbox',
            'drive': 'google-drive',
            'gdrive': 'google-drive',
            'sheets': 'google-sheets',
            'docs': 'google-docs',
            'calendar': 'google-calendar',
            'gmail': 'google-mail',
            # Business Tools
            'hubspot': 'hubspot',
            'crm': 'hubspot',
            'salesforce': 'salesforce',
            'sf': 'salesforce',
            'stripe': 'stripe',
            'payment': 'stripe',
            'twilio': 'twilio',
            'sms': 'twilio',
            'zoom': 'zoom',
            'meet': 'zoom',
            # Content Management
            'wordpress': 'wordpress',
            'wp': 'wordpress',
            'cms': 'wordpress'
        }

    def _run(self, provider: str, endpoint: str, method: str = "GET",
              params: Optional[Dict[str, Any]] = None,
              description: Optional[str] = None) -> str:
        """
        Führt einen universellen API-Call über Tyk aus.

        Args:
            provider: API-Provider (mit Aliases möglich)
            endpoint: API-Endpoint
            method: HTTP-Methode
            params: Request-Parameter
            description: Optionale Beschreibung

        Returns:
            API-Response als formatierter String
        """
        try:
            import requests

            # Provider-Alias auflösen
            resolved_provider = self._resolve_provider(provider)

            # Validierung
            if not self._validate_provider(resolved_provider):
                return f"❌ Unbekannter Provider: {provider}. Verwende einen der folgenden: {list(self.provider_aliases.values())}"

            logger.info(f"🌐 Universeller API-Call: {method} {resolved_provider}:{endpoint}")
            if description:
                logger.info(f"📝 Beschreibung: {description}")

            # Bestimme listen_path für diese API
            listen_path = self.provider_listen_paths.get(resolved_provider, f'/proxy/{resolved_provider}')
            # Stelle sicher, dass listen_path mit / beginnt und nicht mit / endet (außer es ist root)
            if not listen_path.startswith('/'):
                listen_path = '/' + listen_path
            # Entferne trailing slash
            listen_path = listen_path.rstrip('/')
            
            # Tyk-Proxy-URL konstruieren
            proxy_url = f"{self.tyk_url}{listen_path}{endpoint}"

            # Tyk-Header für Target-API
            headers = {
                'X-Target-API': resolved_provider,
                'Content-Type': 'application/json'
            }

            # Request-Daten vorbereiten
            request_kwargs = {
                'method': method.upper(),
                'url': proxy_url,
                'headers': headers,
                'timeout': 30
            }

            # Parameter hinzufügen
            if params:
                if method.upper() in ['POST', 'PUT', 'PATCH']:
                    request_kwargs['json'] = params
                else:
                    request_kwargs['params'] = params

            # API-Call ausführen
            response = requests.request(**request_kwargs)

            # Response verarbeiten
            if response.status_code >= 200 and response.status_code < 300:
                try:
                    result = response.json()
                    return self._format_response(result, resolved_provider, endpoint, method)
                except:
                    return self._format_response({'text': response.text}, resolved_provider, endpoint, method)
            else:
                return f"❌ HTTP {response.status_code}: {response.text}"

        except Exception as e:
            logger.error(f"❌ Fehler im universellen API-Tool: {e}")
            return f"❌ API-Fehler: {str(e)}"

    def _resolve_provider(self, provider: str) -> str:
        """Löst Provider-Aliases auf"""
        provider_lower = provider.lower().strip()
        return self.provider_aliases.get(provider_lower, provider_lower)

    def _validate_provider(self, provider: str) -> bool:
        """Validiert, ob der Provider unterstützt wird"""
        supported_providers = set(self.provider_aliases.values())
        return provider in supported_providers

    def _format_response(self, result: Dict[str, Any], provider: str,
                        endpoint: str, method: str) -> str:
        """Formatiert die API-Response für bessere Lesbarkeit"""

        if 'error' in result:
            return f"❌ API-Fehler ({provider}): {result['error']}"

        # Erfolgreiche Response
        response_data = result
        if isinstance(result, dict) and 'text' in result:
            response_data = result['text']

        # JSON formatieren
        try:
            if isinstance(response_data, (dict, list)):
                formatted_json = json.dumps(response_data, indent=2, ensure_ascii=False)
                return f"✅ {method} {provider}{endpoint} erfolgreich:\n{formatted_json}"
            else:
                return f"✅ {method} {provider}{endpoint}: {response_data}"
        except:
            return f"✅ {method} {provider}{endpoint}: {response_data}"

    def get_supported_providers(self) -> List[str]:
        """Gibt alle unterstützten Provider zurück"""
        return sorted(list(set(self.provider_aliases.values())))

    def get_provider_info(self, provider: str) -> Dict[str, Any]:
        """Gibt Informationen über einen Provider zurück"""
        resolved_provider = self._resolve_provider(provider)

        provider_info = {
            'name': resolved_provider,
            'supported': self._validate_provider(resolved_provider),
            'aliases': [alias for alias, p in self.provider_aliases.items() if p == resolved_provider],
            'description': self._get_provider_description(resolved_provider)
        }

        return provider_info

    def _get_provider_description(self, provider: str) -> str:
        """Gibt eine Beschreibung für einen Provider zurück"""
        descriptions = {
            'github': 'Repository-Management, Issues, Pull Requests, GitHub Actions',
            'notion': 'Datenbanken, Pages, Dokumente, Projekt-Management',
            'slack': 'Messaging, Channels, Notifications, Team-Kommunikation',
            'openai': 'KI-Modelle, Text-Generierung, Chat-Completions',
            'discord': 'Community-Management, Bots, Server-Administration',
            'figma': 'Design-Tools, Prototyping, Team-Kollaboration',
            'dropbox': 'Datei-Speicher, Synchronisation, Sharing',
            'google-drive': 'Datei-Management, Dokumente, Sheets, Slides',
            'hubspot': 'CRM, Marketing Automation, Sales Pipeline',
            'salesforce': 'Enterprise CRM, Sales, Service Cloud',
            'stripe': 'Zahlungsabwicklung, Subscriptions, Billing',
            'twilio': 'SMS, Voice, Video, Kommunikation',
            'zoom': 'Video-Konferenzen, Meetings, Webinars',
            'wordpress': 'Content-Management, Posts, Pages, Media, Comments'
        }

        return descriptions.get(provider, f'API-Integration für {provider}')

    def list_common_endpoints(self, provider: str) -> List[Dict[str, str]]:
        """Gibt häufig verwendete Endpoints für einen Provider zurück"""
        resolved_provider = self._resolve_provider(provider)

        common_endpoints = {
            'github': [
                {'endpoint': '/user', 'method': 'GET', 'description': 'Aktueller Benutzer'},
                {'endpoint': '/user/repos', 'method': 'GET', 'description': 'Benutzer-Repositories'},
                {'endpoint': '/user/repos', 'method': 'POST', 'description': 'Repository erstellen'},
                {'endpoint': '/repos/{owner}/{repo}/issues', 'method': 'GET', 'description': 'Repository-Issues'},
                {'endpoint': '/repos/{owner}/{repo}/issues', 'method': 'POST', 'description': 'Issue erstellen'}
            ],
            'notion': [
                {'endpoint': '/users', 'method': 'GET', 'description': 'Notion-Benutzer'},
                {'endpoint': '/databases', 'method': 'GET', 'description': 'Verfügbare Datenbanken'},
                {'endpoint': '/databases', 'method': 'POST', 'description': 'Datenbank erstellen'},
                {'endpoint': '/pages', 'method': 'POST', 'description': 'Page erstellen'},
                {'endpoint': '/search', 'method': 'POST', 'description': 'Suche in Workspace'}
            ],
            'slack': [
                {'endpoint': '/auth.test', 'method': 'POST', 'description': 'Authentifizierung testen'},
                {'endpoint': '/channels.list', 'method': 'GET', 'description': 'Channels auflisten'},
                {'endpoint': '/chat.postMessage', 'method': 'POST', 'description': 'Nachricht senden'},
                {'endpoint': '/users.list', 'method': 'GET', 'description': 'Team-Mitglieder'},
                {'endpoint': '/files.upload', 'method': 'POST', 'description': 'Datei hochladen'}
            ],
            'openai': [
                {'endpoint': '/models', 'method': 'GET', 'description': 'Verfügbare Modelle'},
                {'endpoint': '/chat/completions', 'method': 'POST', 'description': 'Chat-Completion'},
                {'endpoint': '/images/generations', 'method': 'POST', 'description': 'Bilder generieren'},
                {'endpoint': '/embeddings', 'method': 'POST', 'description': 'Embeddings erstellen'},
                {'endpoint': '/audio/transcriptions', 'method': 'POST', 'description': 'Audio transkribieren'}
            ],
            'wordpress': [
                {'endpoint': '/posts', 'method': 'GET', 'description': 'Posts auflisten'},
                {'endpoint': '/posts', 'method': 'POST', 'description': 'Neuen Post erstellen'},
                {'endpoint': '/posts/{id}', 'method': 'GET', 'description': 'Post abrufen'},
                {'endpoint': '/posts/{id}', 'method': 'PUT', 'description': 'Post aktualisieren'},
                {'endpoint': '/posts/{id}', 'method': 'DELETE', 'description': 'Post löschen'},
                {'endpoint': '/pages', 'method': 'GET', 'description': 'Pages auflisten'},
                {'endpoint': '/pages', 'method': 'POST', 'description': 'Neue Page erstellen'},
                {'endpoint': '/media', 'method': 'GET', 'description': 'Media-Dateien auflisten'},
                {'endpoint': '/media', 'method': 'POST', 'description': 'Media-Datei hochladen'},
                {'endpoint': '/comments', 'method': 'GET', 'description': 'Kommentare auflisten'},
                {'endpoint': '/users', 'method': 'GET', 'description': 'Benutzer auflisten'},
                {'endpoint': '/categories', 'method': 'GET', 'description': 'Kategorien auflisten'},
                {'endpoint': '/tags', 'method': 'GET', 'description': 'Tags auflisten'}
            ]
        }

        return common_endpoints.get(resolved_provider, [])


# Hilfsfunktionen für einfache Verwendung
def get_universal_api_tool() -> UniversalAPITool:
    """Factory-Funktion für das universelle API-Tool"""
    return UniversalAPITool()


def list_supported_providers() -> List[str]:
    """Gibt alle unterstützten Provider zurück"""
    tool = get_universal_api_tool()
    return tool.get_supported_providers()
