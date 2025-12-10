"""
Event Listener für CrewAI Streaming Integration.

Dieses Modul implementiert einen Event-Listener, der LLMStreamChunkEvent Events
von CrewAI abfängt und die gestreamten Tokens verarbeitet, um sie sauber
innerhalb des CrewAI Frameworks zu integrieren.
"""

import threading
import queue
from typing import Any
from crewai.utilities.streaming import LLMStreamChunkEvent, crewai_event_bus


class StreamingEventListener:
    """
    Event Listener für LLM Streaming Events.
    
    Diese Klasse fängt LLMStreamChunkEvent Events ab und stellt die Tokens
    über eine Queue für die Verarbeitung zur Verfügung.
    """
    
    def __init__(self):
        self.token_queue = queue.Queue()
        self._consumer_thread = None
        self._running = False
        self._event_handler = None
        
    def setup_listeners(self):
        """Registriert Event-Listener für LLMStreamChunkEvent."""
        @crewai_event_bus.on(LLMStreamChunkEvent)
        def on_llm_stream_chunk(source: Any, event: LLMStreamChunkEvent):
            """Handler für LLMStreamChunkEvent - fügt Token zur Queue hinzu."""
            token = event.chunk
            if token:
                self.token_queue.put(token)
        self._event_handler = on_llm_stream_chunk
    
    def start_consumer(self, callback=None):
        """
        Startet einen Consumer-Thread, der Tokens aus der Queue verarbeitet.
        
        Args:
            callback: Optionaler Callback, der für jedes Token aufgerufen wird.
                     Wenn nicht angegeben, werden Tokens einfach gesammelt.
        """
        self._running = True
        
        def consumer():
            collected_tokens = []
            while self._running:
                try:
                    # Timeout von 1 Sekunde, um auf neue Tokens zu warten
                    token = self.token_queue.get(timeout=1)
                    
                    if callback:
                        callback(token)
                    else:
                        collected_tokens.append(token)
                        
                    self.token_queue.task_done()
                    
                except queue.Empty:
                    # Timeout abgelaufen, prüfe ob noch läuft
                    continue
                except Exception as e:
                    print(f"Error in token consumer: {e}")
                    break
            
            return collected_tokens
        
        self._consumer_thread = threading.Thread(target=consumer, daemon=True)
        self._consumer_thread.start()
        
    def stop_consumer(self):
        """Stoppt den Consumer-Thread."""
        self._running = False
        if self._consumer_thread:
            self._consumer_thread.join(timeout=2)
            
    def get_all_tokens(self, timeout=5):
        """
        Sammelt alle Tokens aus der Queue.
        
        Args:
            timeout: Timeout in Sekunden
            
        Returns:
            Liste aller gesammelten Tokens
        """
        tokens = []
        try:
            while True:
                token = self.token_queue.get(timeout=timeout)
                tokens.append(token)
                self.token_queue.task_done()
        except queue.Empty:
            pass
            
        return tokens


# Globaler Event Listener für einfachen Zugriff
streaming_event_listener = StreamingEventListener()

# Event Listener registrieren
streaming_event_listener.setup_listeners()


def print_streaming_tokens():
    """
    Beispiel-Funktion: Druckt gestreamte Tokens in Echtzeit.
    
    Diese Funktion zeigt, wie man den Event Listener verwendet,
    um Tokens in Echtzeit zu verarbeiten.
    """
    print("🎯 Streaming aktiviert - Tokens werden in Echtzeit angezeigt:")
    
    def token_callback(token):
        print(token, end='', flush=True)
    
    streaming_event_listener.start_consumer(callback=token_callback)
    
    # Warte auf Abschluss
    try:
        while streaming_event_listener._consumer_thread.is_alive():
            streaming_event_listener._consumer_thread.join(timeout=0.1)
    except KeyboardInterrupt:
        streaming_event_listener.stop_consumer()
        
    print()  # Neue Zeile nach Streaming


def collect_streaming_response(timeout=10):
    """
    Sammelt eine gestreamte Antwort und gibt sie als String zurück.
    
    Args:
        timeout: Timeout in Sekunden
        
    Returns:
        Vollständige Antwort als String
    """
    collected_tokens = []
    
    def token_callback(token):
        collected_tokens.append(token)
    
    streaming_event_listener.start_consumer(callback=token_callback)
    
    # Warte auf Abschluss
    try:
        streaming_event_listener._consumer_thread.join(timeout=timeout)
    except KeyboardInterrupt:
        pass
    finally:
        streaming_event_listener.stop_consumer()
    
    return ''.join(collected_tokens)
