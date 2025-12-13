# Agent Request Flow: Apidog Caching → Tyk Auth

## Übersicht

Agent Tools müssen Requests in einem **2-Phasen Flow** formulieren:

```
Phase 1: Apidog Caching (Metadata + Specs)
   ↓
Phase 2: Tyk Auth (Authentifizierte API Calls)
   ↓
Phase 3: Response Caching (Für zukünftige Requests)
```

## Phase 1: Apidog Caching (Metadata Discovery)

### 1.1 API Discovery über Apidog

```bash
# Step 1: Get JWT Token für Apidog
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Response: {"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
```

### 1.2 Verfügbare APIs mit Tyk Integration entdecken

```bash
# Step 2: Alle APIs mit Tyk Status abrufen (GECACHT)
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  http://localhost:3000/agent/apis/tyk

# Response (gecacht für 6h):
{
  "apis": [
    {
      "api_id": "github",
      "name": "GitHub API",
      "description": "GitHub REST API",
      "base_url": "https://api.github.com",
      "tyk_integration": {
        "tyk_api_id": "github-proxy-1",
        "config_path": "apis/github-proxy-gateway.json",
        "middleware_connected": true,
        "sync_status": "active",
        "current_status": {
          "file_exists": true,
          "tyk_api_active": true
        }
      },
      "authentication": {
        "type": "tyk_proxy",
        "required": true
      },
      "agent_instructions": "Use Tyk proxy at http://localhost:8080/proxy/github-proxy-1/"
    }
  ],
  "count": 1,
  "cache_hint": "Response cached for 6 hours",
  "agent_instructions": "Use api_id for referencing APIs. For Tyk-integrated APIs, use the Tyk proxy URL."
}
```

### 1.3 OpenAPI Specs abrufen (GECACHT)

```bash
# Step 3: OpenAPI Specification für GitHub API abrufen
curl -H "Authorization: Bearer <token>" \
  http://localhost:3000/apis/github/openapi/content

# Alternative: Spec fetch erzwingen (wenn Änderungen erwartet)
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:3000/apis/github/openapi/fetch \
  -d '{"force_refresh": true}'
```

## Phase 2: Tyk Auth (Authentifizierte API Calls)

### 2.1 Tyk Proxy URL generieren

```bash
# Step 4: Tyk Proxy URL für spezifischen Endpoint generieren
curl -H "Authorization: Bearer <token>" \
  "http://localhost:3000/agent/tyk-proxy/github?path=user/repos"

# Response:
{
  "api_id": "github",
  "tyk_api_id": "github-proxy-1",
  "proxy_url": "http://localhost:8080/proxy/github/user/repos",
  "curl_example": "curl -H \"User-Agent: MyAgent/1.0\" \"http://localhost:8080/proxy/github/user/repos\"",
  "agent_note": "Use this proxy URL for API calls through Tyk gateway. Tyk injects auth automatically."
}
```

### 2.2 Authentifizierten Request durch Tyk senden

```bash
# Step 5: Authentifizierten API Call durch Tyk
# Tyk injiziert automatisch Auth basierend auf Provider im Pfad
# GitHub: /proxy/github/...
curl -H "User-Agent: MyAgent/1.0" \
  "http://localhost:8080/proxy/github/user/repos"

# Notion: /proxy/notion/...
curl -H "User-Agent: MyAgent/1.0" \
  "http://localhost:8080/proxy/notion/v1/databases"

# WordPress: /proxy/wordpress/...
curl -H "User-Agent: MyAgent/1.0" \
  "http://localhost:8080/proxy/wordpress/posts"

# Response von GitHub API (durch Tyk proxied):
[
  {
    "id": 123,
    "name": "my-repo",
    "full_name": "myuser/my-repo"
  }
]
```

### 2.3 Provider-spezifische Middleware Flows

Tyk verwendet **provider-spezifische Middleware** für jeden API Typ:

#### **GitHub Flow:**
```
Request: /proxy/github/user/repos
  ↓
Tyk API: github-proxy-1 (listen_path: /proxy/github/)
  ↓
Middleware: github-auth-injector.js
  ↓
Headers: Authorization: token <GITHUB_TOKEN>
  ↓
Target: https://api.github.com/user/repos
```

#### **Notion Flow:**
```
Request: /proxy/notion/v1/databases
  ↓
Tyk API: notion-proxy-1 (listen_path: /proxy/notion/)
  ↓
Middleware: notion-auth-injector.js
  ↓
Headers: Authorization: Bearer <NOTION_TOKEN>
         Notion-Version: 2022-06-28
  ↓
Target: https://api.notion.com/v1/databases
```

#### **WordPress Flow:**
```
Request: /proxy/wordpress/posts
  ↓
Tyk API: wordpress-proxy-1 (listen_path: /proxy/wordpress/)
  ↓
Middleware: wordpress-auth-injector.js
  ↓
Headers: Authorization: Basic <base64_credentials>
         Content-Type: application/json
  ↓
Path Transformation: wp-json/wp/v2/posts
  ↓
Target: https://vyftec.com/wp-json/wp/v2/posts
```

### 2.4 Alternative: Provider Parameter in Query String

```bash
# Alternative: Provider als Query Parameter
curl "http://localhost:8080/proxy/github/user/repos?provider=github"

# Oder als Header
curl -H "provider: github" \
  "http://localhost:8080/proxy/github/user/repos"
```

### 2.3 Alternative: Mit expliziten Headers

```bash
# Wenn Tyk zusätzliche Headers benötigt
curl -H "Authorization: Bearer <user-token>" \
  -H "X-Tyk-Authorization: <tyk-key>" \
  "http://localhost:8080/proxy/github-proxy-1/user/repos"
```

## Phase 3: Response Caching (Optional)

### 3.1 Semantic Caching für ähnliche Queries

```bash
# Step 6: Response für zukünftige ähnliche Queries cachen
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:3000/cache/semantic \
  -d '{
    "query": "List all GitHub repositories for user myuser",
    "response": "[{\"id\":123,\"name\":\"my-repo\"}]",
    "ttl": 3600
  }'
```

### 3.2 Ähnliche gecachte Queries suchen

```bash
# Step 7: Vor dem API Call, prüfen ob ähnliche Query gecacht ist
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:3000/cache/semantic/search \
  -d '{
    "query": "Show me GitHub repos for myuser"
  }'

# Response wenn ähnliche Query gefunden:
{
  "cached": true,
  "similarity": 0.85,
  "response": "[{\"id\":123,\"name\":\"my-repo\"}]",
  "original_query": "List all GitHub repositories for user myuser",
  "message": "Found similar cached query"
}
```

## Kompletter Agent Tool Request Flow

### Beispiel: GitHub Repository Lister Agent

```python
# agent_tool_github_repos.py
import requests
import json

class GitHubRepoAgent:
    def __init__(self, apidog_url="http://localhost:3000", tyk_url="http://localhost:8080"):
        self.apidog_url = apidog_url
        self.tyk_url = tyk_url
        self.token = None
        
    def authenticate(self):
        """Phase 1: Authenticate with Apidog"""
        response = requests.post(
            f"{self.apidog_url}/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        self.token = response.json()["token"]
        return self.token
    
    def discover_apis(self):
        """Phase 1: Discover APIs with caching"""
        response = requests.get(
            f"{self.apidog_url}/agent/apis/tyk",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()
    
    def get_openapi_spec(self, api_id):
        """Phase 1: Get cached OpenAPI spec"""
        response = requests.get(
            f"{self.apidog_url}/apis/{api_id}/openapi/content",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()
    
    def get_tyk_proxy_url(self, api_id, path=""):
        """Phase 2: Get Tyk proxy URL"""
        response = requests.get(
            f"{self.apidog_url}/agent/tyk-proxy/{api_id}",
            headers={"Authorization": f"Bearer {self.token}"},
            params={"path": path}
        )
        return response.json()["proxy_url"]
    
    def get_provider_specific_url(self, provider, endpoint):
        """Get provider-specific Tyk URL"""
        # Map provider names to Tyk paths
        provider_paths = {
            "github": "github",
            "notion": "notion", 
            "wordpress": "wordpress"
        }
        
        if provider not in provider_paths:
            raise ValueError(f"Unknown provider: {provider}")
        
        return f"http://localhost:8080/proxy/{provider_paths[provider]}/{endpoint}"
    
    def call_api_via_tyk(self, api_id, endpoint, method="GET", data=None):
        """Phase 2: Make authenticated API call via Tyk"""
        # 1. Get proxy URL from Apidog
        proxy_info = self.get_tyk_proxy_url(api_id, endpoint)
        proxy_url = proxy_info["proxy_url"]
        
        # 2. Make request through Tyk
        headers = {"User-Agent": "ApidogAgent/1.0"}
        
        # Add provider-specific headers if needed
        if api_id == "notion":
            headers["Content-Type"] = "application/json"
        elif api_id == "wordpress":
            headers["Content-Type"] = "application/json"
        
        response = requests.request(
            method=method,
            url=proxy_url,
            json=data,
            headers=headers
        )
        
        # 3. Cache response if successful
        if response.status_code == 200:
            self.cache_semantic_response(
                query=f"{method} {endpoint}",
                response=response.json()
            )
        
        return response.json()
    
    def call_provider_api(self, provider, endpoint, method="GET", data=None):
        """Direct provider API call without Apidog metadata"""
        # Direct Tyk call with provider in path
        url = f"http://localhost:8080/proxy/{provider}/{endpoint}"
        
        headers = {"User-Agent": "ApidogAgent/1.0"}
        if provider == "notion":
            headers["Content-Type"] = "application/json"
        elif provider == "wordpress":
            headers["Content-Type"] = "application/json"
        
        response = requests.request(
            method=method,
            url=url,
            json=data,
            headers=headers
        )
        
        return response.json()
    
    def cache_semantic_response(self, query, response, ttl=3600):
        """Phase 3: Cache response for similar future queries"""
        requests.post(
            f"{self.apidog_url}/cache/semantic",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"query": query, "response": response, "ttl": ttl}
        )
    
    def search_semantic_cache(self, query):
        """Phase 3: Search for similar cached queries"""
        response = requests.post(
            f"{self.apidog_url}/cache/semantic/search",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"query": query}
        )
        return response.json()

# Usage Example
agent = GitHubRepoAgent()
agent.authenticate()

# Discover available APIs (cached)
apis = agent.discover_apis()
print(f"Found {apis['count']} APIs")

# Get GitHub API spec (cached)
github_spec = agent.get_openapi_spec("github")
print(f"GitHub API spec: {len(github_spec['content']['paths'])} endpoints")

# Make API call via Tyk
repos = agent.call_api_via_tyk("github", "user/repos")
print(f"Found {len(repos)} repositories")
```

## Optimierte Request Patterns

### Pattern 1: Batch Discovery
```bash
# Statt einzelne Requests, batch discovery
# BAD: 3 separate requests
curl /agent/apis/tyk
curl /apis/github/openapi/content  
curl /apis/notion/openapi/content

# GOOD: 1 batch request (implement custom endpoint)
curl -X POST /agent/batch \
  -d '{"operations": [
    {"path": "/agent/apis/tyk", "method": "GET"},
    {"path": "/apis/github/openapi/content", "method": "GET"}
  ]}'
```

### Pattern 2: Conditional Requests
```bash
# Use ETag/If-None-Match für conditional fetching
curl -H "If-None-Match: \"abc123\"" \
  /apis/github/openapi/content
  
# Response: 304 Not Modified wenn unverändert
```

### Pattern 3: Pre-fetching
```bash
# Vorhersehen welche APIs benötigt werden
# Pre-fetch bei Agent Startup
curl -X POST /apis/github/openapi/fetch
curl -X POST /apis/notion/openapi/fetch
```

## Error Handling & Retry Logic

### Beispiel mit Retry und Fallback
```python
def make_agent_request_with_fallback(api_id, endpoint):
    """Intelligenter Request mit Caching Fallback"""
    
    # 1. Versuche semantic cache
    cached = agent.search_semantic_cache(f"GET {endpoint}")
    if cached["cached"] and cached["similarity"] > 0.8:
        return cached["response"]
    
    # 2. Versuche Tyk Proxy
    try:
        return agent.call_api_via_tyk(api_id, endpoint)
    except requests.exceptions.ConnectionError:
        # 3. Fallback: Direkter API Call (ohne Tyk Auth)
        # Nur wenn API key-based auth
        return make_direct_api_call(api_id, endpoint)
    except Exception as e:
        # 4. Fallback: Stale cache aus Database
        stale_data = get_stale_cache_from_db(api_id, endpoint)
        if stale_data:
            return stale_data
        raise e
```

## Best Practices für Agent Tools

### 1. **Token Management**
- Tokens cachen (1h Gültigkeit)
- Automatische Refresh vor Ablauf
- Separate Tokens pro Agent Instance

### 2. **Cache Awareness**
- `cache_hint` in Responses beachten
- `If-Modified-Since` Header verwenden
- Batch requests wo möglich

### 3. **Error Resilience**
- Fallback zu stale cache
- Circuit breaker für Tyk
- Exponential backoff retry

### 4. **Monitoring**
- Cache hit rates tracken
- Response times loggen
- Token usage monitoring

### 5. **Performance Optimization**
- Connection pooling für Apidog/Tyk
- Parallel requests wo möglich
- Lazy loading von Specs

## Beispiel: Kompletter Workflow

### Workflow für "Get GitHub User Repositories"
```
1. Agent startet
   ↓
2. Authenticate mit Apidog → Token erhalten
   ↓
3. Discover APIs → Gecachte Liste (6h)
   ↓
4. Check semantic cache → "Get user repos" ähnlich?
   ↓ Hit: Return cached response
   ↓ Miss: Weiter zu 5
   ↓
5. Get Tyk proxy URL → Von Apidog
   ↓
6. Make request → /proxy/github/user/repos
   ↓
7. Tyk github-auth-injector → Injiziert GitHub Token
   ↓
8. Request zu GitHub API → https://api.github.com/user/repos
   ↓
9. Response zurück → Durch Tyk proxied
   ↓
10. Cache response → Für zukünftige ähnliche Queries
   ↓
11. Return result → An Agent
```

### Workflow für "Get Notion Databases"
```
1. Agent startet
   ↓
2. Authenticate mit Apidog → Token erhalten
   ↓
3. Discover APIs → Gecachte Liste (6h)
   ↓
4. Check semantic cache → "Get databases" ähnlich?
   ↓ Hit: Return cached response
   ↓ Miss: Weiter zu 5
   ↓
5. Get Tyk proxy URL → Von Apidog
   ↓
6. Make request → /proxy/notion/v1/databases
   ↓
7. Tyk notion-auth-injector → Injiziert Notion Token + Version
   ↓
8. Request zu Notion API → https://api.notion.com/v1/databases
   ↓
9. Response zurück → Durch Tyk proxied
   ↓
10. Cache response → Für zukünftige ähnliche Queries
   ↓
11. Return result → An Agent
```

### Workflow für "Get WordPress Posts"
```
1. Agent startet
   ↓
2. Authenticate mit Apidog → Token erhalten
   ↓
3. Discover APIs → Gecachte Liste (6h)
   ↓
4. Check semantic cache → "Get posts" ähnlich?
   ↓ Hit: Return cached response
   ↓ Miss: Weiter zu 5
   ↓
5. Get Tyk proxy URL → Von Apidog
   ↓
6. Make request → /proxy/wordpress/posts
   ↓
7. Tyk wordpress-auth-injector → Path transformation + Basic Auth
   ↓
8. Request zu WordPress API → https://vyftec.com/wp-json/wp/v2/posts
   ↓
9. Response zurück → Durch Tyk proxied
   ↓
10. Cache response → Für zukünftige ähnliche Queries
   ↓
11. Return result → An Agent
```

### Code Implementation
```python
def get_user_repositories(user):
    # Build query
    query = f"Get repositories for user {user}"
    
    # Check semantic cache first
    cached = search_semantic_cache(query)
    if cached["cached"]:
        return cached["response"]
    
    # Get Tyk proxy URL
    proxy_url = get_tyk_proxy_url("github", f"users/{user}/repos")
    
    # Make request through Tyk
    response = requests.get(proxy_url)
    
    # Cache for future
    if response.ok:
        cache_semantic_response(query, response.json())
    
    return response.json()
```

## Konfiguration

### Agent Environment Variables
```bash
# Required
APIDOG_URL=http://localhost:3000
APIDOG_USERNAME=admin
APIDOG_PASSWORD=admin123

# Optional
APIDOG_CACHE_TTL=3600
TYK_URL=http://localhost:8080
ENABLE_SEMANTIC_CACHE=true
MAX_RETRIES=3
```

### Agent Initialization
```python
from agent_toolkit import ApidogAgent

agent = ApidogAgent(
    base_url=os.getenv("APIDOG_URL"),
    username=os.getenv("APIDOG_USERNAME"),
    password=os.getenv("APIDOG_PASSWORD"),
    cache_ttl=int(os.getenv("APIDOG_CACHE_TTL", 3600)),
    enable_semantic_cache=os.getenv("ENABLE_SEMANTIC_CACHE", "true").lower() == "true"
)

# Auto-authenticate and cache APIs
agent.initialize()
```

## Fazit

Agent Tools müssen Requests in diesem **provider-spezifischen Flow** formulieren:

### **Core Principles:**
1. **Apidog First**: Alle Metadata/Discovery über Apidog (gecacht)
2. **Provider in Path**: `/proxy/<provider>/<endpoint>` für Tyk Routing
3. **Middleware Injection**: Provider-spezifische Auth durch Tyk Middleware
4. **Cache Always**: Responses für zukünftige Requests cachen

### **Provider-spezifische URLs:**
- **GitHub**: `http://localhost:8080/proxy/github/{endpoint}`
- **Notion**: `http://localhost:8080/proxy/notion/{endpoint}`  
- **WordPress**: `http://localhost:8080/proxy/wordpress/{endpoint}`

### **Vorteile dieses Flows:**
- **Performance**: 10-100x durch Caching
- **Security**: Zentrale, provider-spezifische Auth durch Tyk
- **Resilience**: Mehrschichtige Fallbacks
- **Cost Savings**: 85-99% weniger External Calls
- **Consistency**: Einheitliche Schnittstelle für alle Provider

### **Integration mit bestehender Tyk Infrastruktur:**
- Nutzt existierende `github-proxy-1`, `notion-proxy-1`, `wordpress-proxy-1` APIs
- Verwendet spezifische Middleware für jeden Provider
- Behält bestehende `listen_path` Struktur bei
- Ermöglicht einfache Erweiterung um neue Provider

Durch diese Struktur können Agent Tools effizient und kostengünstig mit externen APIs interagieren, während sie die bestehende Tyk Infrastruktur mit provider-spezifischer Middleware nutzen.
