"""
Streaming Client für llama.cpp Integration in CrewAI

Dieses Modul bietet Streaming-Funktionalität für llama.cpp Server,
um Token in Echtzeit zu streamen anstatt auf komplette Antworten zu warten.
"""

import requests
import json
import time
import random
from typing import Generator, Optional, List, Dict
from .settings import settings


class LlamaStreamingClient:
    """Client für Streaming von llama.cpp Server-Antworten"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialisiert den Streaming-Client.
        
        Args:
            base_url: Basis-URL des llama.cpp Servers (default: aus settings)
            timeout: Timeout in Sekunden für Requests
        """
        self.base_url = base_url or settings.llm_base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Accept-Encoding': 'identity',  # Verhindert gzip-Kompression für Streaming
            'Content-Type': 'application/json',
            'User-Agent': 'CrewAI-Llama-Streaming-Client/1.0'
        })
    
    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Streamt Chat-Antworten token-by-token.
        
        Args:
            messages: Liste von Nachrichten im OpenAI-Format
            model: Modellname (default: aus settings)
            temperature: Temperature für Sampling (default: aus settings)
            max_tokens: Maximale Tokens in Antwort (default: aus settings)
            **kwargs: Zusätzliche Parameter für llama.cpp API
            
        Yields:
            Jedes generierte Token als String
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        # Use server-compatible model name
        model_name = model or settings.llm_model
        # Convert model name to server format if needed
        if "llama-3-2" in model_name.lower():
            model_name = "Llama-3.2-3B-Instruct-Q4_K_M"
        
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            "temperature": temperature or settings.llm_temperature,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            **kwargs
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
                                # Handle both content and reasoning_content
                                if 'content' in delta and delta['content'] is not None:
                                    yield delta['content']
                                elif 'reasoning_content' in delta and delta['reasoning_content'] is not None:
                                    yield delta['reasoning_content']
                        except json.JSONDecodeError:
                            continue
        
        except requests.exceptions.RequestException as e:
            yield f"\n[Streaming Error: {str(e)}]"
    
    def stream_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Streamt Text-Vervollständigungen token-by-token.
        
        Args:
            prompt: Eingabe-Prompt
            model: Modellname (default: aus settings)
            temperature: Temperature für Sampling (default: aus settings)
            max_tokens: Maximale Tokens in Antwort (default: aus settings)
            **kwargs: Zusätzliche Parameter für llama.cpp API
            
        Yields:
            Jedes generierte Token als String
        """
        url = f"{self.base_url}/v1/completions"
        
        # Use server-compatible model name
        model_name = model or settings.llm_model
        # Convert model name to server format if needed
        if "llama-3-2" in model_name.lower():
            model_name = "Llama-3.2-3B-Instruct-Q4_K_M"
        
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": True,
            "temperature": temperature or settings.llm_temperature,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            **kwargs
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
                            if 'choices' in chunk:
                                for choice in chunk['choices']:
                                    if 'text' in choice:
                                        yield choice['text']
                        except json.JSONDecodeError:
                            continue
        
        except requests.exceptions.RequestException as e:
            yield f"\n[Streaming Error: {str(e)}]"
    
    def stream_with_retry(
        self,
        stream_func,
        *args,
        max_retries: int = 3,
        base_delay: float = 1.0,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Streamt mit automatischen Retries bei Fehlern.
        
        Args:
            stream_func: Streaming-Funktion (stream_chat oder stream_completion)
            *args: Argumente für stream_func
            max_retries: Maximale Anzahl Retry-Versuche
            base_delay: Basis-Verzögerung für exponentielles Backoff
            **kwargs: Keyword-Argumente für stream_func
            
        Yields:
            Jedes generierte Token als String
        """
        retries = 0
        while retries < max_retries:
            try:
                for token in stream_func(*args, **kwargs):
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
    
    def check_server_health(self) -> bool:
        """
        Prüft die Gesundheit des llama.cpp Servers.
        
        Returns:
            True wenn Server erreichbar und gesund, sonst False
        """
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def close(self):
        """Schließt die Session und gibt Ressourcen frei."""
        self.session.close()


class AsyncLlamaStreamingClient:
    """Asynchroner Client für Streaming (für Web-APIs)"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialisiert den asynchronen Streaming-Client.
        
        Args:
            base_url: Basis-URL des llama.cpp Servers (default: aus settings)
            timeout: Timeout in Sekunden für Requests
        """
        self.base_url = base_url or settings.llm_base_url
        self.timeout = timeout
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Asynchrones Streaming von Chat-Antworten.
        
        Args:
            messages: Liste von Nachrichten im OpenAI-Format
            model: Modellname (default: aus settings)
            temperature: Temperature für Sampling (default: aus settings)
            **kwargs: Zusätzliche Parameter für llama.cpp API
            
        Yields:
            Jedes generierte Token als String
        """
        import httpx
        
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": model or settings.llm_model,
            "messages": messages,
            "stream": True,
            "temperature": temperature or settings.llm_temperature,
            **kwargs
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


# Singleton-Instanz für einfache Verwendung
streaming_client = LlamaStreamingClient()


def demonstrate_streaming():
    """Demonstriert die Streaming-Funktionalität"""
    print("🧪 Demonstrating llama.cpp streaming...")
    
    # Teste Server-Health
    if not streaming_client.check_server_health():
        print("❌ Server nicht erreichbar. Bitte llama-server starten.")
        return
    
    print("✅ Server ist erreichbar")
    
    # Beispiel 1: Chat-Streaming
    print("\n1. Chat-Streaming Demo:")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in 2 sentences."}
    ]
    
    print("Prompt:", messages[1]["content"])
    print("Response: ", end='', flush=True)
    
    full_response = ""
    for token in streaming_client.stream_chat(messages, max_tokens=100):
        print(token, end='', flush=True)
        full_response += token
    
    print(f"\n\nVollständige Antwort ({len(full_response)} chars): {full_response[:100]}...")
    
    # Beispiel 2: Completion-Streaming mit Retry
    print("\n2. Completion-Streaming mit Retry Demo:")
    prompt = "The future of artificial intelligence will"
    
    print(f"Prompt: {prompt}")
    print("Streaming with retry: ", end='', flush=True)
    
    try:
        for token in streaming_client.stream_with_retry(
            streaming_client.stream_completion,
            prompt,
            max_tokens=50,
            temperature=0.8
        ):
            print(token, end='', flush=True)
        print()
    except Exception as e:
        print(f"\n❌ Fehler nach Retries: {e}")


if __name__ == "__main__":
    demonstrate_streaming()
