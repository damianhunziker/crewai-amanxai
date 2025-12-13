# WordPress Direct API Integration

Das universelle API Tool unterstützt jetzt direkte WordPress API Aufrufe im folgenden Format:

```json
{
  "provider": "wordpress",
  "endpoint": "/posts",
  "method": "GET",
  "params": {"status": "publish"}
}
```

## Unterstützte Provider-Aliases

- `wordpress` oder `wp` oder `cms`

## Häufig verwendete WordPress Endpoints

### Posts
- `GET /posts` - Alle Posts auflisten
- `POST /posts` - Neuen Post erstellen
- `GET /posts/{id}` - Einzelnen Post abrufen
- `PUT /posts/{id}` - Post aktualisieren
- `DELETE /posts/{id}` - Post löschen

### Pages
- `GET /pages` - Alle Pages auflisten
- `POST /pages` - Neue Page erstellen

### Media
- `GET /media` - Media-Dateien auflisten
- `POST /media` - Datei hochladen

### Andere
- `GET /comments` - Kommentare auflisten
- `GET /users` - Benutzer auflisten
- `GET /categories` - Kategorien auflisten
- `GET /tags` - Tags auflisten

## Beispiel-Verwendung in Agenten

```python
from crewai import Agent, Task
from core.universal_nango_api_tool import UniversalAPITool

agent = Agent(
    role="WordPress Manager",
    goal="Verwalte WordPress-Inhalte",
    tools=[UniversalAPITool()],
    llm=llm
)

task = Task(
    description="""
    Rufe alle veröffentlichten WordPress Posts ab:

    {
      "provider": "wordpress",
      "endpoint": "/posts",
      "method": "GET",
      "params": {"status": "publish"}
    }
    """,
    agent=agent
)
```

## Parameter

- **provider**: `"wordpress"`, `"wp"`, oder `"cms"`
- **endpoint**: WordPress REST API Endpoint (z.B. `"/posts"`, `"/pages/{id}"`)
- **method**: HTTP-Methode (`"GET"`, `"POST"`, `"PUT"`, `"DELETE"`)
- **params**: Request-Parameter
  - Bei `GET`: Query-Parameter (z.B. `{"status": "publish", "per_page": 10}`)
  - Bei `POST`/`PUT`: Request-Body (z.B. `{"title": "Neuer Post", "content": "..."}`)

## Vorteile

✅ **Direkte API Integration** - Keine zusätzlichen Tools nötig
✅ **Vollständige WordPress REST API** - Alle Endpoints verfügbar
✅ **Streaming-kompatibel** - Funktioniert mit Streaming LLMs
✅ **Einheitliches Format** - Gleiche Syntax für alle APIs