# Llama.cpp Streaming Implementation für unser Setup

## Aktuelle Situation

Unser Setup verwendet:
- **llama-server** auf Port 5020 (CPU-Modus wegen Vulkan-Problemen)
- **CrewAI** als Framework für LLM-Integration
- **Einfache Start-Konfiguration**: `./llama.cpp/build/bin/llama-server -m ./models/Qwen3-4B-Q5_K_M.gguf --gpu-layers 0 --host 0.0.0.0 --port 5020 --ctx-size 2048 --threads 4`
- **LLM-Konfiguration** in `core/settings.py`: `llm_base_url = "http://localhost:5020"`

## Streaming-Funktionalität in llama.cpp

### Server-Seitige Konfiguration

Für optimiertes Streaming sollte der llama-server mit folgenden Parametern gestartet werden:

```bash
./llama.cpp/build/bin/llama-server \
  -m ./models/Qwen3-4B-Q5_K_M.gguf \
  --host 0.0.0.0 \
  --port 5020 \
  --ctx-size 2048 \
  --threads 8 \
  --gpu-layers 0 \
  --cont-batching \
  --parallel 4 \
  --threads-http 4 \
  --timeout 300
```

**Erklärung der Parameter:**
- `--cont-batching`: Aktiviert kontinuierliches Batching für bessere GPU/CPU-Auslastung
- `--parallel 4`: Ermöglicht 4 parallele Anfragen (Slots)
- `--threads-http 4`: 4 HTTP-Verarbeitungs-Threads für bessere Concurrent-Connection-Handling
- `--timeout 300`: 5 Minuten Timeout für lange Streaming-Sessions

### API-Endpunkte für Streaming

Der llama-server bietet zwei Haupt-API-Endpunkte:

1. **Chat Completions** (für Dialoge):
   ```
   POST http://localhost:5020/v1/chat/completions
   ```
   ```json
   {
     "model": "Qwen3-4B-Q5_K_M.gguf",
     "messages": [
       {"role": "system", "content": "You are a helpful assistant."},
       {"role": "user", "content": "Explain quantum computing"}
     ],
     "stream": true,
     "temperature": 0.7,
     "max_tokens": 1000
   }
   ```

2. **Completions** (für Text-Vervollständigung):
   ```
   POST http://localhost:5020/v1/completions
   ```
   ```json
   {
     "model": "Qwen3-4B-Q5_K_M.gguf",
     "prompt": "Once upon a time",
     "stream": true,
     "temperature": 0.7,
     "max_tokens": 500
   }
   ```

## Python-Client-Implementierung

### Option 1: Synchron mit requests (einfach)

```python
import requests
import json

class LlamaStreamingClient:
    def __init__(self, base_url="http://localhost:5020", timeout=30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Accept-Encoding': 'identity',  # Verhindert gzip-Kompression
            'Content-Type': 'application/json'
        })
    
    def stream_chat(self, messages, model="Qwen3-4B-Q5_K_M.gguf", temperature=0.7, max_tokens=1000):
        """Streamt Chat-Antworten token-by-token"""
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = self.session.post(
                url,
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        json_str = decoded_line[6:].strip()
                        if json_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(json_str)
                            if 'choices' in chunk and chunk['choices']:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield delta['content']
                        except json.JSONDecodeError:
                            continue
        
        except requests.exceptions.RequestException as e:
            yield f"\n[Error: {str(e)}]"
    
    def close(self):
        self.session.close()

# Verwendung
client = LlamaStreamingClient()
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain quantum computing in simple terms"}
]

print("Assistant: ", end='', flush=True)
for token in client.stream_chat(messages):
    print(token, end='', flush=True)
print()
client.close()
```

### Option 2: Asynchron mit httpx (für Web-APIs)

```python
import httpx
import json
import asyncio

class AsyncLlamaStreamingClient:
    def __init__(self, base_url="http://localhost:5020", timeout=30):
        self.base_url = base_url
        self.timeout = httpx.Timeout(timeout)
    
    async def stream_chat(self, messages, model="Qwen3-4B-Q5_K_M.gguf", temperature=0.7):
        """Asynchrones Streaming von Chat-Antworten"""
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        json_str = line[6:].strip()
                        if json_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(json_str)
                            if 'choices' in chunk and chunk['choices']:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield delta['content']
                        except json.JSONDecodeError:
                            continue

# Verwendung in FastAPI
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import json

app = FastAPI()
llama_client = AsyncLlamaStreamingClient()

@app.post("/chat/stream")
async def chat_stream(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    
    async def generate():
        async for token in llama_client.stream_chat(messages):
            yield json.dumps({"token": token}) + "\n"
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

## Integration mit CrewAI

### Erweiterung des LLM-Routers für Streaming

```python
# core/llm_router_streaming.py
from typing import Generator, AsyncGenerator
import requests
import json
from .settings import settings

class StreamingLLMClient:
    def __init__(self):
        self.base_url = settings.llm_base_url
        self.session = requests.Session()
        self.session.headers.update({'Accept-Encoding': 'identity'})
    
    def stream_completion(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """Streamt Text-Vervollständigungen"""
        url = f"{self.base_url}/v1/completions"
        payload = {
            "model": settings.llm_model,
            "prompt": prompt,
            "stream": True,
            "temperature": kwargs.get("temperature", settings.llm_temperature),
            "max_tokens": kwargs.get("max_tokens", settings.llm_max_tokens)
        }
        
        response = self.session.post(url, json=payload, stream=True, timeout=60)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    json_str = decoded_line[6:].strip()
                    if json_str == '[DONE]':
                        break
                    try:
                        chunk = json.loads(json_str)
                        if 'choices' in chunk:
                            for choice in chunk['choices']:
                                if 'text' in choice:
                                    yield choice['text']
                    except json.JSONDecodeError:
                        continue
    
    def stream_chat(self, messages: list, **kwargs) -> Generator[str, None, None]:
        """Streamt Chat-Antworten"""
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "stream": True,
            "temperature": kwargs.get("temperature", settings.llm_temperature),
            "max_tokens": kwargs.get("max_tokens", settings.llm_max_tokens)
        }
        
        response = self.session.post(url, json=payload, stream=True, timeout=60)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    json_str = decoded_line[6:].strip()
                    if json_str == '[DONE]':
                        break
                    try:
                        chunk = json.loads(json_str)
                        if 'choices' in chunk and chunk['choices']:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                    except json.JSONDecodeError:
                        continue

# Singleton-Instanz
streaming_llm_client = StreamingLLMClient()
```

## Best Practices für stabiles Streaming

### 1. Connection Management
- **Session-Pooling**: Immer dieselbe Session wiederverwenden
- **Keep-Alive**: TCP-Verbindungen offen halten für wiederholte Requests
- **Connection Limits**: Maximal 4-8 parallele Verbindungen zum Server

### 2. Error Handling und Retry-Logik
```python
import time
import random

def stream_with_retry(client, prompt, max_retries=3, base_delay=1):
    """Streamt mit automatischen Retries bei Fehlern"""
    retries = 0
    while retries < max_retries:
        try:
            for token in client.stream_completion(prompt):
                yield token
            return
        except requests.exceptions.Timeout:
            retries += 1
            if retries >= max_retries:
                raise
            delay = base_delay * (2 ** retries) + random.uniform(0, 1)
            time.sleep(delay)
        except requests.exceptions.ConnectionError:
            retries += 1
            if retries >= max_retries:
                raise
            delay = base_delay * (2 ** retries)
            time.sleep(delay)
```

### 3. Timeout-Konfiguration
- **Connect-Timeout**: 5-10 Sekunden
- **Read-Timeout**: 30-60 Sekunden (länger für langsame Generierungen)
- **Stream-Timeout**: 300 Sekunden für lange Sessions

### 4. Server Health Monitoring
```python
def check_server_health(base_url="http://localhost:5020"):
    """Prüft Server-Health über /health Endpunkt"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# Regelmäßige Health-Checks
import schedule
import time

def monitor_server_health():
    if not check_server_health():
        print("Server nicht erreichbar, starte neu...")
        # Server neu starten
        subprocess.run(["./scripts/start_llama_cpu.sh"])

# Alle 5 Minuten prüfen
schedule.every(5).minutes.do(monitor_server_health)
```

### 5. Performance-Optimierung
- **Token-Caching**: System-Prompts konsistent halten für Cache-Wiederverwendung
- **Batch-Verarbeitung**: Mehrere Anfragen parallel mit `--parallel` Parameter
- **Context-Size**: Auf 2048 Tokens begrenzen für bessere Performance
- **Thread-Konfiguration**: `--threads 8` für 8-Core CPU

## Implementierungsplan für unser Setup

### Phase 1: Server-Optimierung
1. **Start-Skript aktualisieren** (`scripts/start_llama_optimized.sh`):
   ```bash
   #!/bin/bash
   ./llama.cpp/build/bin/llama-server \
     -m ./models/Qwen3-4B-Q5_K_M.gguf \
     --host 0.0.0.0 \
     --port 5020 \
     --ctx-size 2048 \
     --threads 8 \
     --gpu-layers 0 \
     --cont-batching \
     --parallel 4 \
     --threads-http 4 \
     --timeout 300 \
     --log-format json
   ```

2. **Health-Check Endpunkt aktivieren**:
   - Standardmäßig verfügbar unter `/health`
   - Für Monitoring in Prometheus/Grafana

### Phase 2: Client-Implementierung
1. **Streaming-Client Klasse erstellen** (`core/llm_streaming_client.py`)
2. **Integration in CrewAI LLM-Router**
3. **Async-Client für Web-APIs** (`core/async_llm_client.py`)

### Phase 3: Testing und Monitoring
1. **Unit-Tests für Streaming** (`test/test_streaming.py`)
2. **Performance-Metriken sammeln**:
   - Tokens pro Sekunde
   - Latenz bis zum ersten Token
   - Connection-Stabilität
3. **Error-Recovery implementieren**

### Phase 4: Production-Ready Features
1. **Circuit-Breaker Pattern** für Server-Überlastung
2. **Load-Balancing** bei mehreren llama-server Instanzen
3. **Rate-Limiting** für API-Endpunkte
4. **Logging und Tracing** für Debugging

## Häufige Probleme und Lösungen

### Problem 1: Kein Streaming, alles auf einmal
**Lösung**: `Accept-Encoding: identity` Header setzen, um gzip-Kompression zu verhindern

### Problem 2: Verbindungsabbrüche
**Lösung**: Timeouts erhöhen und Retry-Logik implementieren

### Problem 3: Langsame Token-Generierung
**Lösung**:
- Kleinere Modelle verwenden (z.B. Llama-3.2-3B statt Qwen3-4B)
- Context-Size reduzieren
- CPU-Threads optimieren

### Problem 4: Memory-Leaks bei langen Sessions
**Lösung**: Regelmäßige Server-Neustarts und Memory-Monitoring

## Empfehlungen für unser Setup

1. **Starten mit CPU-Modus**: Wegen Vulkan-Problemen weiterhin CPU verwenden
2. **Parallelität erhöhen**: `--parallel 4` für bessere Auslastung
3. **Streaming aktivieren**: In allen Client-Implementierungen `stream=True` setzen
4. **Monitoring implementieren**: Health-Checks und Performance-Metriken
5. **Fallback-Strategie**: Bei Streaming-Fehlern auf nicht-streamende Requests zurückfallen

## Beispiel: Vollständige Integration

```python
# main.py - Beispielintegration
from core.llm_streaming_client import streaming_llm_client
from core.settings import settings

def demonstrate_streaming():
    print("Demonstrating llama.cpp streaming...")
    
    # Beispiel 1: Text-Vervollständigung
    prompt = "Once upon a time in a galaxy far, far away"
    print(f"Prompt: {prompt}")
    print("Streaming response: ", end='', flush=True)
    
    for token in streaming_llm_client.stream_completion(prompt,
