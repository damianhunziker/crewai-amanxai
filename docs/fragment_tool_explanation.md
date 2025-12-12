# Fragment-Based API Tool: Wie es OpenAPI-Specs findet und über Apidog verfügbar macht

## Übersicht

Das Fragment-basierte API-Tool ermöglicht es LLMs, OpenAPI-Spezifikationen selbstständig auszulesen und API-Calls zu generieren. Hier ist die detaillierte Erklärung, wie es funktioniert:

## 1. Architektur

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Agent         │    │ Fragment Tool   │    │   Apidog        │
│   (CrewAI)      │◄──►│ (fragment_based │◄──►│   Service       │
│                 │    │ _api_tool.py)   │    │   (Port 3000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Fragment      │    │   Universal     │    │   OpenAPI       │
│   Cache         │    │   Nango Tool    │    │   Specs DB      │
│   (SQLite)      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 2. Wie das Tool OpenAPI-Specs findet

### 2.1 Lokaler Fragment-Cache
- **Datenbank**: `api_fragments.db` (SQLite)
- **Inhalt**: Extrahiere Fragmente aus OpenAPI-Specs
- **Struktur**:
  - `fragments` Tabelle: Endpunkte, Schemas, Parameter
  - `api_metadata` Tabelle: API-Informationen
  - `fragment_relationships`: Abhängigkeiten zwischen Fragmenten

### 2.2 Apidog als API-Registry
- **Service**: Node.js-Service auf Port 3000
- **Funktion**: Zentrale Registrierung von APIs mit OpenAPI-Specs
- **Registrierte APIs** (siehe `setup_apidog_apis.py`):
  - GitHub, Notion, OpenAI, Slack, Discord
  - Google Calendar, Stripe, Twilio, Figma
  - **WordPress REST API** (Ja, WordPress ist hinterlegt!)

### 2.3 WordPress API in Apidog
```python
{
    "id": "wordpress",
    "name": "WordPress REST API",
    "category": "cms",
    "description": "Posts, Pages, Users und Custom Content verwalten",
    "base_url": "https://your-site.com/wp-json/wp/v2",
    "auth_type": "api_key",
    "policies": {
        "rate_limit_per_hour": 5000,
        "max_concurrent_calls": 10,
        "timeout_seconds": 30,
        "retry_attempts": 2,
        "auth_refresh": False
    }
}
```

## 3. Workflow: Wie ein Agent eine API erforscht

### Schritt 1: Intent-Analyse
```python
# Agent sagt: "I want to create a WordPress post"
user_intent = "I want to create a WordPress post"
api_id = "wordpress"
```

### Schritt 2: Fragment-Suche
```python
# Fragment-Tool sucht im Cache
relevant_fragments = fragment_cache.find_fragments_by_intent(
    api_id="wordpress",
    intent="create a WordPress post"
)
```

### Schritt 3: Falls keine Fragmente gefunden
1. **Apidog abfragen**: `GET http://localhost:3000/apis/wordpress`
2. **OpenAPI-Spec laden**: Von `openapi_spec_url` in Apidog
3. **Fragmente extrahieren**: `extract_fragments_from_spec()`
4. **Im Cache speichern**: Für zukünftige Verwendung

### Schritt 4: Interpretation
```python
# Heuristische oder LLM-basierte Interpretation
config = interpreter.interpret_intent_with_fragments(
    user_intent="I want to create a WordPress post",
    api_id="wordpress",
    fragments=relevant_fragments
)

# Ergebnis:
# - Endpoint: POST /posts
# - Method: POST
# - Parameters: {"title": "...", "content": "...", "status": "publish"}
# - Confidence: 80%
```

## 4. Integration mit Apidog

### 4.1 API-Registrierung
```bash
# APIs in Apidog registrieren
python scripts/setup_apidog_apis.py

# Apidog Service starten
cd /Users/jgtcdghun/workspace/apidog
npm start
```

### 4.2 OpenAPI-Specs speichern
Apidog kann OpenAPI-Specs auf verschiedene Arten speichern:
1. **Direkt in der Datenbank**: `openapi_spec_url` Feld
2. **Externe URLs**: Verweis auf öffentliche OpenAPI-Specs
3. **Lokale Dateien**: Speicherung im Dateisystem

### 4.3 Fragment-Tool Zugriff auf Apidog
```python
# In fragment_based_api_tool.py
def _load_spec_from_apidog(api_id: str):
    """Lädt OpenAPI-Spec von Apidog"""
    response = requests.get(
        f"{settings.apidog_base_url}/apis/{api_id}"
    )
    if response.status_code == 200:
        api_info = response.json()
        openapi_spec_url = api_info.get('openapi_spec_url')
        
        if openapi_spec_url:
            spec_response = requests.get(openapi_spec_url)
            return spec_response.json()
    
    return None
```

## 5. Beispiel: WordPress API nutzen

### 5.1 WordPress-Fragmente im Cache
```
Fragment 1:
- Type: endpoint
- Content: {"path": "/posts", "method": "POST"}
- Metadata: {"summary": "Create a post", "keywords": ["post", "create", "wordpress"]}

Fragment 2:
- Type: endpoint  
- Content: {"path": "/posts/{id}", "method": "GET"}
- Metadata: {"summary": "Retrieve a post", "keywords": ["post", "get", "retrieve"]}
```

### 5.2 Agent-Request
```python
result = fragment_api_tool._run(
    user_intent="Create a new blog post about AI",
    api_id="wordpress",
    additional_params={
        "title": "The Future of AI",
        "content": "AI is transforming...",
        "status": "draft"
    }
)
```

### 5.3 Ergebnis
```
🔍 API Research Results
API ID: wordpress
Confidence: 80%
Reasoning: Heuristic match based on keywords: ['post', 'create', 'wordpress']

🚀 Recommended API Call
Endpoint: POST /posts
Parameters: {
  "title": "The Future of AI",
  "content": "AI is transforming...",
  "status": "draft"
}
Description: Create a post
```

## 6. Vorteile des Fragment-basierten Ansatzes

### 6.1 Lazy Loading
- Nur relevante Teile der OpenAPI-Spec werden geladen
- Reduziert Speicher- und Netzwerk-Overhead
- Schnellere Response-Zeiten

### 6.2 Cache-Optimierung
- Häufig verwendete Fragmente bleiben im Cache
- Nutzungsstatistiken für Performance-Optimierung
- Automatische Bereinigung alter Fragmente

### 6.3 Apidog-Integration
- Zentrale API-Registry
- OpenAPI-Spec Management
- Authentifizierung und Monitoring

## 7. Nächste Schritte

### 7.1 WordPress OpenAPI-Spec hinzufügen
```python
# WordPress OpenAPI-Spec zu Apidog hinzufügen
wordpress_spec = {
    "openapi": "3.0.0",
    "info": {
        "title": "WordPress REST API",
        "version": "2.0.0"
    },
    "paths": {
        "/posts": {
            "get": {"summary": "List posts"},
            "post": {"summary": "Create post"}
        },
        "/posts/{id}": {
            "get": {"summary": "Retrieve post"},
            "put": {"summary": "Update post"},
            "delete": {"summary": "Delete post"}
        }
    }
}

# In Apidog speichern
requests.post(f"{APIDOG_URL}/apis/wordpress/spec", json=wordpress_spec)
```

### 7.2 Fragment-Tool erweitern
- Direkte Apidog-Integration
- Automatische Spec-Aktualisierung
- Bessere Fehlerbehandlung

## 8. Fazit

Das Fragment-basierte API-Tool **findet OpenAPI-Specs über Apidog** und macht sie über einen lokalen Fragment-Cache verfügbar. **WordPress API Specs sind in Apidog hinterlegt** und können vom Tool verwendet werden. Der Ansatz ermöglicht es LLMs, jede API autonom zu erforschen, die über OpenAPI-Specs verfügbar ist – ohne spezifischen Code für jede API schreiben zu müssen.
