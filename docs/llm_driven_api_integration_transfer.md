# 🔄 Transfer zur LLM-gesteuerten API-Integration

## 🎯 Übersicht der neuen Architektur

Die Integration wechselt von **fest definierten API-Tools** zu einem **LLM-gesteuerten, dynamischen API-System**. Anstatt für jede API spezifische Funktionen zu implementieren, nutzt das LLM OpenAPI-Spezifikationen um dynamisch zu entscheiden, welche API-Calls ausgeführt werden müssen.

### **Neue Architektur: LLM als API-Interpreter**

```
Agent Request → LLM (versteht Intent) → OpenAPI Spec → Dynamic Tool → API Call
```

## 📁 Dateien-Übersicht

### **Vorhandene Dateien (bleiben erhalten)**

#### **Kern-Authentifizierung**
- [`src/core/apidog_auth_client.py`](src/core/apidog_auth_client.py) - Token-Management
- [`src/core/apidog_bitwarden_integration.py`](src/core/apidog_bitwarden_integration.py) - Bitwarden-Integration
- [`src/core/universal_bitwarden_integration.py`](src/core/universal_bitwarden_integration.py) - Universal Bitwarden Tool

#### **API Discovery**
- [`src/core/zulpo_client.py`](src/core/zulpo_client.py) - Zuplo API Discovery Client
- [`src/core/apidog_integration.py`](src/core/apidog_integration.py) - Apidog Integration

#### **Konfiguration**
- [`src/config/settings.py`](src/config/settings.py) - API-URLs und Timeouts
- [`.env.example`](.env.example) - Environment-Variablen Template

### **Neue Dateien (müssen erstellt werden)**

#### **LLM-gesteuertes API-Tool**
- [`src/core/llm_driven_api_tool.py`]() - Haupt-Tool Klasse
- [`src/core/openapi_llm_interpreter.py`]() - LLM-Logik für API-Verständnis
- [`src/core/dynamic_api_executor.py`]() - API-Call Ausführung

#### **Policies und Sicherheit**
- [`src/core/api_policies.py`]() - Auth-Policies für verschiedene API-Typen
- [`src/core/llm_api_security.py`]() - Sicherheitsvalidierung für LLM-generierte Calls
- [`src/core/rate_limiting.py`]() - API Rate Limiting

#### **Erweiterte Authentifizierung**
- [`src/core/oauth2_automation.py`]() - Vollautomatische OAuth2-Integration
- [`src/core/api_key_manager.py`]() - Verbessertes API-Key Management
- [`src/core/token_refresh_scheduler.py`]() - Automatische Token-Auffrischung

#### **Integration und Management**
- [`src/core/llm_api_manager.py`]() - Manager für LLM-API-Integrationen
- [`src/agents/dynamic_api_agent.py`]() - Agent mit dynamischen API-Fähigkeiten

### **Modifizierte Dateien**

#### **Manager Agent**
- [`src/agents/manager.py`](src/agents/manager.py) - Integration des neuen LLM-API-Tools

#### **Konfiguration**
- [`src/config/settings.py`](src/config/settings.py) - Neue LLM-API Einstellungen

## 🏗️ Implementierungsplan

### **Phase 1: Kern-Komponenten**

#### **1.1 LLM-Driven API Tool**
```python
class LLMDrivenAPITool(BaseTool):
    """LLM-gesteuertes Tool für dynamische API-Calls"""

    def __init__(self, api_id: str, openapi_spec: Dict):
        self.api_id = api_id
        self.openapi_spec = openapi_spec
        self.llm_interpreter = OpenAPILLMInterpreter()
        self.auth_manager = APISecurityManager()

    def _run(self, user_intent: str, **kwargs) -> str:
        # 1. LLM interpretiert Intent
        api_call = self.llm_interpreter.interpret_intent(
            user_intent, self.openapi_spec
        )

        # 2. Sicherheit prüfen
        self.auth_manager.validate_api_call(api_call)

        # 3. Auth-Token holen
        token = self._get_auth_token()

        # 4. API-Call ausführen
        return self._execute_api_call(api_call, token)
```

#### **1.2 OpenAPI LLM Interpreter**
```python
class OpenAPILLMInterpreter:
    """Nutzt LLM um OpenAPI Specs zu verstehen"""

    def interpret_intent(self, user_intent: str, openapi_spec: Dict) -> APICall:
        prompt = f"""
        Analysiere diese User-Anfrage und die OpenAPI Spec.
        Finde den passenden API-Endpoint und Parameter.

        User Intent: {user_intent}
        OpenAPI Spec: {json.dumps(openapi_spec, indent=2)}

        Gib ein JSON zurück mit:
        - endpoint: Der API-Pfad
        - method: HTTP-Methode
        - parameters: Erforderliche Parameter
        - description: Was der Call macht
        """

        llm_response = self.llm.generate(prompt)
        return self._parse_llm_response(llm_response)
```

### **Phase 2: Authentifizierung & Sicherheit**

#### **2.1 API Policies**
```python
class APIPolicies:
    """Policies für verschiedene API-Typen"""

    OAUTH2_POLICY = {
        "automatic_auth": True,
        "token_refresh": True,
        "scope_validation": True,
        "rate_limiting": "adaptive"
    }

    API_KEY_POLICY = {
        "manual_setup": True,
        "token_validation": True,
        "rotation_reminder": 30,
        "exposure_detection": True
    }
```

#### **2.2 LLM Security Layer**
```python
class LLMapiSecurity:
    """Sicherheitsvalidierung für LLM-generierte API-Calls"""

    def validate_api_call(self, api_call: APICall) -> bool:
        # 1. Endpoint existiert in OpenAPI Spec
        # 2. Parameter sind valide
        # 3. Keine gefährlichen Operationen
        # 4. Rate Limiting prüfen
        pass

    def sanitize_parameters(self, params: Dict) -> Dict:
        # SQL-Injection, XSS, etc. verhindern
        pass
```

### **Phase 3: Integration in Manager Agent**

#### **3.1 Dynamic API Manager**
```python
class DynamicAPIManager:
    """Verwaltet alle verfügbaren APIs für den Agenten"""

    def __init__(self):
        self.available_apis = {}
        self.llm_tools = {}
        self._discover_and_setup_apis()

    def _discover_and_setup_apis(self):
        # 1. APIs via Zuplo entdecken
        apis = zulpo_client.discover_apis()

        # 2. Für jede API: OpenAPI Spec laden
        for api in apis:
            spec = zulpo_client.get_api_spec(api['id'])

            # 3. LLM-Driven Tool erstellen
            tool = LLMDrivenAPITool(api['id'], spec)
            self.llm_tools[api['id']] = tool

    def get_tools_for_agent(self, agent_role: str) -> List[BaseTool]:
        # Filtert Tools basierend auf Agent-Rolle
        return [tool for tool in self.llm_tools.values()]
```

#### **3.2 Manager Agent Integration**
```python
# In src/agents/manager.py
class VyftecManagerAgent:
    def __init__(self):
        # ... existing code ...
        self.api_manager = DynamicAPIManager()
        self.llm_api_tools = self.api_manager.get_tools_for_agent("manager")

        # Tools zum Agent hinzufügen
        self.manager_agent = Agent(
            # ... existing config ...
            tools=self.llm_api_tools  # Neue dynamische Tools
        )
```

## 🔐 Authentifizierungsfluss

### **OAuth2 APIs (vollautomatisch)**
```
1. Agent: "Verbinde mit GitHub"
2. LLM Tool: Erkennt OAuth2-Anforderung
3. OAuth2 Automation: Startet Flow
4. User: Authorization-Link klicken
5. Token: Automatisch in Bitwarden gespeichert
6. Future Calls: Token automatisch verwendet
```

### **API-Key APIs (halbautomatisch)**
```
1. Agent: "Brauche OpenAI API Key"
2. LLM Tool: Erkennt API-Key-Anforderung
3. API Key Manager: Zeigt Setup-Instruktionen
4. User: Erstellt Key und speichert in Bitwarden
5. System: Erkennt neuen Key automatisch
6. Future Calls: Key automatisch verwendet
```

## 📋 Erforderliche Erweiterungen

### **Zuplo Auth Policies**
```yaml
# policies/zulpo_auth_policies.yaml
oauth2_policies:
  automatic_discovery: true
  token_refresh_buffer: 300  # Sekunden vor Ablauf refreshen
  scope_validation: strict
  max_tokens_per_api: 10

api_key_policies:
  manual_validation: true
  key_rotation_days: 90
  exposure_alerts: enabled
  backup_keys: 2
```

### **LLM API Security**
- **Intent Validation**: LLM-Output auf gefährliche Patterns prüfen
- **Parameter Sanitization**: SQL-Injection und XSS verhindern
- **Rate Limiting**: Pro API und User
- **Audit Logging**: Alle API-Calls loggen

### **Monitoring & Observability**
- **API Call Metrics**: Success/Failure rates pro API
- **Token Health**: Automatische Token-Validierung
- **LLM Accuracy**: Wie gut das LLM API-Calls identifiziert
- **Security Incidents**: Automatische Alerts

## 🎯 Migrationspfad

### **Schritt 1: Neue Komponenten implementieren**
- LLM-Driven API Tool
- OpenAPI Interpreter
- API Policies

### **Schritt 2: Authentifizierung erweitern**
- OAuth2 Automation
- API Key Manager
- Token Refresh Scheduler

### **Schritt 3: Integration testen**
- GitHub API als Proof of Concept
- OpenAI API für API-Keys
- Notion API für OAuth2

### **Schritt 4: Alte Tools ablösen**
- Bestehende spezifische Tools durch LLM-Tool ersetzen
- Fallback-Mechanismen für kritische APIs

## 🔧 Detaillierte Integrationsanleitung

### **Phase 1: Neue Kern-Komponenten erstellen**

#### **1.1 LLM-Driven API Tool** 📄
**Speicherort**: `src/core/llm_driven_api_tool.py`

```python
# src/core/llm_driven_api_tool.py
from typing import Dict, Any, Optional
from crewai.tools import BaseTool
import json
import logging

from .openapi_llm_interpreter import OpenAPILLMInterpreter
from .llm_api_security import LLMapiSecurity
from .apidog_auth_client import ApidogAuthClient

logger = logging.getLogger(__name__)

class LLMDrivenAPITool(BaseTool):
    """LLM-gesteuertes Tool für dynamische API-Calls"""

    name: str = "llm_api_tool"
    description: str = "Führt API-Calls basierend auf OpenAPI-Specs und LLM-Verständnis aus"

    def __init__(self, api_id: str, openapi_spec: Dict, api_base_url: str):
        super().__init__()
        self.api_id = api_id
        self.openapi_spec = openapi_spec
        self.api_base_url = api_base_url
        self.llm_interpreter = OpenAPILLMInterpreter()
        self.security_manager = LLMapiSecurity()
        self.auth_client = ApidogAuthClient()
        self.name = f"llm_api_tool_{api_id}"
        self.description = f"LLM-gesteuerter Zugriff auf {api_id} API"

    def _run(self, user_intent: str, **kwargs) -> str:
        """Führt LLM-gesteuerten API-Call aus"""
        try:
            logger.info(f"🔄 Processing intent for {self.api_id}: {user_intent}")

            # 1. LLM interpretiert Intent basierend auf OpenAPI Spec
            api_call_config = self.llm_interpreter.interpret_intent(
                user_intent, self.openapi_spec, **kwargs
            )

            # 2. Sicherheitsvalidierung
            if not self.security_manager.validate_api_call(api_call_config, self.openapi_spec):
                return "❌ API-Call wurde aus Sicherheitsgründen blockiert"

            # 3. Authentifizierung
            auth_token = self.auth_client.get_auth_token(self.api_id, "api_key")  # Fallback
            if not auth_token:
                return f"❌ Kein Authentifizierungstoken für {self.api_id} gefunden"

            # 4. API-Call ausführen
            result = self._execute_api_call(api_call_config, auth_token)

            logger.info(f"✅ API-Call erfolgreich für {self.api_id}")
            return result

        except Exception as e:
            logger.error(f"❌ LLM API Tool Fehler für {self.api_id}: {e}")
            return f"❌ Fehler bei API-Call: {str(e)}"

    def _execute_api_call(self, call_config: Dict, auth_token: str) -> str:
        """Führt den tatsächlichen API-Call aus"""
        import requests

        url = f"{self.api_base_url}{call_config['endpoint']}"
        method = call_config.get('method', 'GET').upper()
        params = call_config.get('parameters', {})

        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=params)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params)
            else:
                return f"❌ Nicht unterstützte HTTP-Methode: {method}"

            response.raise_for_status()
            return response.json() if response.content else "✅ Operation erfolgreich"

        except requests.exceptions.RequestException as e:
            return f"❌ API-Fehler: {str(e)}"
```

#### **1.2 OpenAPI LLM Interpreter** 📄
**Speicherort**: `src/core/openapi_llm_interpreter.py`

```python
# src/core/openapi_llm_interpreter.py
from typing import Dict, Any
import json
import logging
from ..core.llm_router import get_llm_for_api_interpretation  # Bestehende LLM-Routing

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

    def interpret_intent(self, user_intent: str, openapi_spec: Dict, **kwargs) -> APICallConfig:
        """Interpretiert User-Intent und erstellt API-Call-Konfiguration"""

        # OpenAPI-Pfade extrahieren
        paths = openapi_spec.get('paths', {})

        prompt = f"""
Du bist ein API-Experte. Analysiere die User-Anfrage und die verfügbaren API-Endpunkte.
Finde den passendsten Endpunkt für die Anfrage.

USER INTENT: "{user_intent}"

VERFÜGBARE ENDPOINTS:
{json.dumps(paths, indent=2)}

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
- Verwende nur Endpoints die in der OpenAPI-Spec existieren
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
```

#### **1.3 LLM API Security** 📄
**Speicherort**: `src/core/llm_api_security.py`

```python
# src/core/llm_api_security.py
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

    def validate_api_call(self, api_call_config: Dict, openapi_spec: Dict) -> bool:
        """Validiert einen API-Call vor Ausführung"""

        # 1. Endpoint existiert in OpenAPI Spec
        if not self._endpoint_exists(api_call_config['endpoint'], openapi_spec):
            logger.warning(f"❌ Endpoint nicht in Spec gefunden: {api_call_config['endpoint']}")
            return False

        # 2. HTTP-Methode ist erlaubt
        allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        if api_call_config.get('method', '').upper() not in allowed_methods:
            logger.warning(f"❌ Nicht erlaubte HTTP-Methode: {api_call_config.get('method')}")
            return False

        # 3. Parameter-Sanitization
        if not self._sanitize_parameters(api_call_config.get('parameters', {})):
            logger.warning("❌ Unsichere Parameter erkannt")
            return False

        # 4. Rate Limiting prüfen
        if not self._check_rate_limit(api_call_config.get('api_id', 'unknown')):
            logger.warning("❌ Rate Limit überschritten")
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
```

### **Phase 2: Bestehende Dateien erweitern**

#### **2.1 Manager Agent Integration** 📝
**Datei**: `src/agents/manager.py`
**Änderungen**: Neue Imports und Integration des DynamicAPIManager

```python
# src/agents/manager.py - NEUE IMPORTS HINZUFÜGEN
from ..core.llm_api_manager import DynamicAPIManager  # NEUE ZEILE
from ..core.llm_driven_api_tool import LLMDrivenAPITool  # NEUE ZEILE

# EXISTIERENDE KLASSE ERWEITERN
class VyftecManagerAgent:
    def __init__(self):
        # ... existing code ...

        # NEUE ZEILEN: LLM-API-Manager initialisieren
        self.dynamic_api_manager = DynamicAPIManager()
        self.llm_api_tools = self.dynamic_api_manager.get_tools_for_agent("manager")

        # EXISTIERENDE TOOLS ERWEITERN
        self.tool_manager = MCPToolManager()
        existing_tools = self.tool_manager.get_tools_for_agent(AgentType.MANAGER)

        # KOMBINIERE alte und neue Tools
        self.all_manager_tools = existing_tools + self.llm_api_tools

        # EXISTIERENDE AGENT-KREATION ANPASSEN
        self.manager_agent = self._create_manager_agent_with_dynamic_tools()

    # NEUE METHODE
    def _create_manager_agent_with_dynamic_tools(self) -> Agent:
        """Erstellt Manager-Agent mit dynamischen LLM-API-Tools"""
        config = AgentConfig(
            role="Vyftec Manager mit LLM-API-Integration",
            goal="Koordiniere alle Agenten und verwende LLM-gesteuerte API-Tools für maximale Flexibilität",
            backstory=(
                "Du bist der zentrale Manager mit Zugriff auf dynamische API-Tools. "
                "Du kannst jede API verwenden, die über OpenAPI-Specs verfügbar ist, "
                "ohne dass spezifischer Code dafür geschrieben werden muss."
            ),
            tools=self.all_manager_tools,  # KOMBINIERTE TOOLS
            temperature=0.2,
            max_tokens=3000,
            model_name="Llama-3.2-3B-Instruct-Q4_K_M.gguf"
        )

        return self._create_agent(AgentType.MANAGER, config)

    # NEUE METHODE für dynamische Tool-Discovery
    def discover_new_api(self, api_name: str) -> str:
        """Entdeckt und integriert eine neue API dynamisch"""
        try:
            # API über Zuplo entdecken
            apis = self.zulpo_client.discover_apis()
            matching_api = next((api for api in apis if api_name.lower() in api['name'].lower()), None)

            if not matching_api:
                return f"❌ API '{api_name}' nicht gefunden"

            # OpenAPI Spec laden
            spec = self.zulpo_client.get_api_spec(matching_api['id'])

            # Neues LLM Tool erstellen
            new_tool = LLMDrivenAPITool(matching_api['id'], spec, matching_api.get('base_url', ''))

            # Tool zur verfügbaren Liste hinzufügen
            self.llm_api_tools.append(new_tool)

            return f"✅ Neue API '{api_name}' erfolgreich integriert"

        except Exception as e:
            return f"❌ Fehler bei API-Integration: {str(e)}"
```

#### **2.2 Settings erweitern** 📝
**Datei**: `src/config/settings.py`
**Änderungen**: Neue Konfiguration für LLM-API-Features

```python
# src/config/settings.py - NEUE FELDER HINZUFÜGEN
class Settings(BaseSettings):
    # ... existing fields ...

    # LLM API Integration Settings - NEUE FELDER
    llm_api_enabled: bool = Field(default=True, description="LLM-gesteuerte API-Tools aktivieren")
    llm_api_security_level: str = Field(default="strict", description="Sicherheitslevel für LLM-API-Calls")
    llm_api_rate_limit: int = Field(default=100, description="Max API-Calls pro Stunde pro API")
    llm_api_cache_enabled: bool = Field(default=True, description="API Response Caching aktivieren")
    llm_api_audit_log: bool = Field(default=True, description="API-Call Auditing aktivieren")

    # OpenAPI LLM Settings
    openapi_llm_model: str = Field(default="Llama-3.2-3B-Instruct-Q4_K_M.gguf", description="LLM für OpenAPI Interpretation")
    openapi_llm_temperature: float = Field(default=0.1, description="Temperature für präzise API-Interpretation")
    openapi_llm_max_tokens: int = Field(default=1000, description="Max Tokens für LLM-Response")

    # API Policies - NEUE SEKTION
    api_policies: Dict[str, Any] = Field(default_factory=lambda: {
        "oauth2": {
            "automatic_refresh": True,
            "refresh_buffer_seconds": 300,
            "max_tokens_per_api": 10
        },
        "api_key": {
            "manual_validation": True,
            "rotation_days": 90,
            "exposure_detection": True
        }
    }, description="API-spezifische Policies")
```

#### **2.3 LLM Router erweitern** 📝
**Datei**: `src/core/llm_router.py`
**Änderungen**: Neue Funktion für API-Interpretation

```python
# src/core/llm_router.py - NEUE FUNKTION HINZUFÜGEN
def get_llm_for_api_interpretation() -> LLM:
    """Gibt LLM-Instanz für OpenAPI Interpretation zurück"""
    from ..config.settings import settings

    return LLM(
        model=f"openai/{settings.openapi_llm_model}",
        temperature=settings.openapi_llm_temperature,
        max_tokens=settings.openapi_llm_max_tokens,
        api_key="no-key-required"
    )
```

### **Phase 3: Dynamic API Manager erstellen**

#### **3.1 LLM API Manager** 📄
**Speicherort**: `src/core/llm_api_manager.py`

```python
# src/core/llm_api_manager.py
from typing import List, Dict, Any
from crewai.tools import BaseTool
import logging

from .zulpo_client import ZuploClient
from .llm_driven_api_tool import LLMDrivenAPITool
from .llm_api_security import LLMapiSecurity

logger = logging.getLogger(__name__)

class DynamicAPIManager:
    """Verwaltet alle verfügbaren LLM-gesteuerten API-Tools"""

    def __init__(self):
        self.zulpo_client = ZuploClient()
        self.security_manager = LLMapiSecurity()
        self.available_apis = {}
        self.llm_tools = {}
        self._initialize_apis()

    def _initialize_apis(self):
        """Lädt alle verfügbaren APIs beim Startup"""
        try:
            logger.info("🔄 Initialisiere Dynamic API Manager...")

            # APIs über Zuplo entdecken
            discovered_apis = self.zulpo_client.discover_apis()

            for api in discovered_apis:
                api_id = api['id']
                try:
                    # OpenAPI Spec laden
                    spec = self.zulpo_client.get_api_spec(api_id)
                    if not spec:
                        logger.warning(f"⚠️ Keine OpenAPI Spec für {api_id}")
                        continue

                    # LLM Tool erstellen
                    base_url = api.get('base_url', self._infer_base_url(api))
                    tool = LLMDrivenAPITool(api_id, spec, base_url)

                    self.llm_tools[api_id] = tool
                    self.available_apis[api_id] = api

                    logger.info(f"✅ LLM Tool für {api_id} erstellt")

                except Exception as e:
                    logger.error(f"❌ Fehler bei API {api_id}: {e}")

            logger.info(f"🎯 {len(self.llm_tools)} LLM API Tools initialisiert")

        except Exception as e:
            logger.error(f"❌ Dynamic API Manager Initialisierung fehlgeschlagen: {e}")

    def _infer_base_url(self, api: Dict) -> str:
        """Inferiert Base-URL aus API-Info"""
        # Fallback-Logik für Base-URLs
        api_id = api['id']
        url_mappings = {
            'github': 'https://api.github.com',
            'notion': 'https://api.notion.com',
            'slack': 'https://slack.com/api',
            'openai': 'https://api.openai.com',
        }
        return url_mappings.get(api_id, f"https://api.{api_id}.com")

    def get_tools_for_agent(self, agent_role: str) -> List[BaseTool]:
        """Gibt Tools für eine Agent-Rolle zurück"""
        # Filter basierend auf Rolle (könnte erweitert werden)
        if agent_role == "manager":
            return list(self.llm_tools.values())
        else:
            # Für andere Rollen nur sichere APIs
            safe_apis = ['github']  # Beispiel-Filter
            return [self.llm_tools[api_id] for api_id in safe_apis if api_id in self.llm_tools]

    def add_new_api(self, api_id: str, openapi_spec: Dict, base_url: str) -> bool:
        """Fügt eine neue API dynamisch hinzu"""
        try:
            tool = LLMDrivenAPITool(api_id, openapi_spec, base_url)
            self.llm_tools[api_id] = tool
            logger.info(f"✅ Neue API {api_id} hinzugefügt")
            return True
        except Exception as e:
            logger.error(f"❌ Fehler beim Hinzufügen von API {api_id}: {e}")
            return False

    def get_available_apis_info(self) -> List[Dict]:
        """Gibt Info über verfügbare APIs zurück"""
        return [
            {
                'id': api_id,
                'name': api.get('name', api_id),
                'description': api.get('description', ''),
                'has_llm_tool': api_id in self.llm_tools
            }
            for api_id, api in self.available_apis.items()
        ]

    def refresh_api_specs(self):
        """Aktualisiert alle OpenAPI Specs"""
        logger.info("🔄 Aktualisiere API Specs...")
        for api_id in list(self.llm_tools.keys()):
            try:
                new_spec = self.zulpo_client.get_api_spec(api_id)
                if new_spec:
                    # Neues Tool mit aktualisierter Spec erstellen
                    api_info = self.available_apis[api_id]
                    base_url = self._infer_base_url(api_info)
                    new_tool = LLMDrivenAPITool(api_id, new_spec, base_url)
                    self.llm_tools[api_id] = new_tool
                    logger.info(f"✅ Spec für {api_id} aktualisiert")
            except Exception as e:
                logger.error(f"❌ Fehler bei Spec-Update für {api_id}: {e}")
```

## 🚀 Vorteile der neuen Architektur

- **🔄 Extrem skalierbar**: Jede API mit OpenAPI-Spec sofort verfügbar
- **🧠 LLM-gesteuert**: Nutzt KI für API-Verständnis
- **🔒 Sicher**: Policies und Validierung verhindern Missbrauch
- **⚡ Schnell**: Kein Entwicklungsaufwand für neue APIs
- **📊 Observabel**: Vollständige Transparenz über API-Nutzung

Diese Architektur verwandelt Vyftec in ein **universelles API-Integrationssystem**, das sich automatisch an neue APIs anpasst und dabei höchste Sicherheitsstandards einhält.