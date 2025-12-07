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

## 🚀 Vorteile der neuen Architektur

- **🔄 Extrem skalierbar**: Jede API mit OpenAPI-Spec sofort verfügbar
- **🧠 LLM-gesteuert**: Nutzt KI für API-Verständnis
- **🔒 Sicher**: Policies und Validierung verhindern Missbrauch
- **⚡ Schnell**: Kein Entwicklungsaufwand für neue APIs
- **📊 Observabel**: Vollständige Transparenz über API-Nutzung

Diese Architektur verwandelt Vyftec in ein **universelles API-Integrationssystem**, das sich automatisch an neue APIs anpasst und dabei höchste Sicherheitsstandards einhält.