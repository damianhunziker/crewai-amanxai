"""
Test-Suite für llama.cpp Streaming-Integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from core.llm_streaming_client import streaming_client, LlamaStreamingClient


def test_server_health():
    """Testet ob der llama.cpp Server erreichbar ist"""
    print("🧪 Teste Server-Health...")
    is_healthy = streaming_client.check_server_health()
    
    if is_healthy:
        print("✅ Server ist erreichbar und gesund")
        return True
    else:
        print("❌ Server nicht erreichbar")
        print("   Bitte starte llama-server mit: ./scripts/start_llama_optimized.sh")
        return False


def test_chat_streaming():
    """Testet Chat-Streaming-Funktionalität"""
    print("\n🧪 Teste Chat-Streaming...")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    
    print(f"Prompt: {messages[1]['content']}")
    print("Streaming response: ", end='', flush=True)
    
    start_time = time.time()
    token_count = 0
    full_response = ""
    
    try:
        for token in streaming_client.stream_chat(messages, max_tokens=50):
            print(token, end='', flush=True)
            full_response += token
            token_count += 1
        
        elapsed = time.time() - start_time
        print(f"\n\n✅ Chat-Streaming erfolgreich")
        print(f"   Tokens: {token_count}")
        print(f"   Zeit: {elapsed:.2f}s")
        print(f"   Antwort: {full_response[:100]}...")
        return True
        
    except Exception as e:
        print(f"\n❌ Chat-Streaming fehlgeschlagen: {e}")
        return False


def test_completion_streaming():
    """Testet Completion-Streaming-Funktionalität"""
    print("\n🧪 Teste Completion-Streaming...")
    
    prompt = "Artificial intelligence is"
    
    print(f"Prompt: {prompt}")
    print("Streaming response: ", end='', flush=True)
    
    start_time = time.time()
    token_count = 0
    full_response = ""
    
    try:
        for token in streaming_client.stream_completion(prompt, max_tokens=30):
            print(token, end='', flush=True)
            full_response += token
            token_count += 1
        
        elapsed = time.time() - start_time
        print(f"\n\n✅ Completion-Streaming erfolgreich")
        print(f"   Tokens: {token_count}")
        print(f"   Zeit: {elapsed:.2f}s")
        print(f"   Antwort: {full_response[:100]}...")
        return True
        
    except Exception as e:
        print(f"\n❌ Completion-Streaming fehlgeschlagen: {e}")
        return False


def test_stream_with_retry():
    """Testet Streaming mit Retry-Logik"""
    print("\n🧪 Teste Streaming mit Retry-Logik...")
    
    prompt = "The benefits of renewable energy include"
    
    print(f"Prompt: {prompt}")
    print("Streaming with retry: ", end='', flush=True)
    
    try:
        token_count = 0
        for token in streaming_client.stream_with_retry(
            streaming_client.stream_completion,
            prompt,
            max_tokens=20,
            temperature=0.8
        ):
            print(token, end='', flush=True)
            token_count += 1
        
        print(f"\n\n✅ Streaming mit Retry erfolgreich")
        print(f"   Tokens: {token_count}")
        return True
        
    except Exception as e:
        print(f"\n❌ Streaming mit Retry fehlgeschlagen: {e}")
        return False


def test_async_client_import():
    """Testet ob der Async-Client importiert werden kann"""
    print("\n🧪 Teste Async-Client Import...")
    
    try:
        from core.llm_streaming_client import AsyncLlamaStreamingClient
        print("✅ AsyncLlamaStreamingClient kann importiert werden")
        return True
    except ImportError as e:
        print(f"❌ Async-Client Import fehlgeschlagen: {e}")
        return False


def test_performance():
    """Testet Performance-Metriken"""
    print("\n🧪 Teste Performance-Metriken...")
    
    if not streaming_client.check_server_health():
        print("❌ Server nicht erreichbar für Performance-Test")
        return False
    
    # Test mit kurzem Prompt für Baseline
    prompt = "Hello"
    
    print("Messe Latenz bis zum ersten Token...")
    
    start_time = time.time()
    first_token_received = False
    first_token_time = None
    token_count = 0
    
    try:
        for token in streaming_client.stream_completion(prompt, max_tokens=10):
            if not first_token_received:
                first_token_time = time.time() - start_time
                first_token_received = True
                print(f"   Erstes Token nach: {first_token_time:.3f}s")
            
            token_count += 1
        
        total_time = time.time() - start_time
        
        if token_count > 0:
            tokens_per_second = token_count / total_time
            print(f"✅ Performance-Test erfolgreich")
            print(f"   Gesamt-Tokens: {token_count}")
            print(f"   Gesamt-Zeit: {total_time:.3f}s")
            print(f"   Tokens/Sekunde: {tokens_per_second:.2f}")
            print(f"   Latenz erstes Token: {first_token_time:.3f}s")
            return True
        else:
            print("❌ Keine Tokens empfangen")
            return False
            
    except Exception as e:
        print(f"❌ Performance-Test fehlgeschlagen: {e}")
        return False


def run_all_tests():
    """Führt alle Tests aus"""
    print("=" * 60)
    print("🧪 Llama.cpp Streaming Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Server Health", test_server_health),
        ("Chat Streaming", test_chat_streaming),
        ("Completion Streaming", test_completion_streaming),
        ("Streaming mit Retry", test_stream_with_retry),
        ("Async Client Import", test_async_client_import),
        ("Performance", test_performance),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Zusammenfassung
    print("\n" + "=" * 60)
    print("📊 Test-Zusammenfassung")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nGesamt: {passed}/{total} Tests bestanden")
    
    if passed == total:
        print("\n🎉 Alle Tests erfolgreich! Streaming ist funktionsfähig.")
        return True
    else:
        print(f"\n⚠️  {total - passed} Tests fehlgeschlagen")
        print("   Überprüfe Server-Konfiguration und Netzwerkverbindung")
        return False


if __name__ == "__main__":
    # Stelle sicher, dass der Client geschlossen wird
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        streaming_client.close()
