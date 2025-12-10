#!/usr/bin/env python3
"""
Test script for the StreamingLLM integration
"""

from core.llm_streaming_client import StreamingLLM
from core.settings import settings

def test_streaming_llm():
    """Test the StreamingLLM class"""
    print("🧪 Testing StreamingLLM...")

    # Create StreamingLLM instance
    llm = StreamingLLM(
        model_name="Qwen3-4B-Q5_K_M",
        base_url="http://localhost:5020/v1"
    )

    # Test messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, what is AI?"}
    ]

    print(f"🤖 Model: {llm.model}")
    print(f"📡 Base URL: {llm.base_url}")
    print(f"🌡️ Temperature: {llm.temperature}")
    print(f"📏 Max Tokens: {llm.max_tokens}")

    print("\n💬 Testing call method...")
    try:
        response = llm.call(messages, max_tokens=50)
        print(f"✅ Response received: {len(response)} characters")
        print(f"📝 Response preview: {response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_streaming_llm()
    if success:
        print("\n🎉 StreamingLLM test PASSED!")
    else:
        print("\n💥 StreamingLLM test FAILED!")