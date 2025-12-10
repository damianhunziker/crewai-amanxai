#!/usr/bin/env python3
"""
Test script to verify main.py imports work correctly with StreamingLLM
"""

import sys
import os

# Add current directory to path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

def test_main_import():
    try:
        # Import the key components from main.py
        from core.llm_streaming_client import StreamingLLM

        # Test creating the LLM instances like in main.py
        local_llm = StreamingLLM(
            model_name="Qwen3-4B-Q5_K_M",
            base_url="http://localhost:5020/v1"
        )

        # Test that the LLM has the expected attributes
        assert hasattr(local_llm, 'call'), "StreamingLLM missing call method"
        assert hasattr(local_llm, 'model'), "StreamingLLM missing model property"
        assert local_llm.model == "Qwen3-4B-Q5_K_M", f"Model name mismatch: {local_llm.model}"

        print("✅ StreamingLLM creation successful")
        print(f"🤖 Model: {local_llm.model}")
        print(f"📡 Base URL: {local_llm.base_url}")

        # Test a simple call (without CrewAI imports to avoid other issues)
        print("\n🧪 Testing simple StreamingLLM call...")
        messages = [{"role": "user", "content": "Hi"}]
        response = local_llm.call(messages, max_tokens=10)
        print(f"✅ Simple call successful: {len(response)} chars")
        print(f"📝 Preview: {response[:50]}...")

        print("\n🎉 All tests PASSED! The ImportError is fixed.")
        return True

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    try:
        # Import the key components from main.py
        from core.llm_streaming_client import StreamingLLM

        # Test creating the LLM instances like in main.py
        local_llm = StreamingLLM(
            model_name="Qwen3-4B-Q5_K_M",
            base_url="http://localhost:5020/v1"
        )

        # Test that the LLM has the expected attributes
        assert hasattr(local_llm, 'call'), "StreamingLLM missing call method"
        assert hasattr(local_llm, 'model'), "StreamingLLM missing model property"
        assert local_llm.model == "Qwen3-4B-Q5_K_M", f"Model name mismatch: {local_llm.model}"

        print("✅ StreamingLLM creation successful")
        print(f"🤖 Model: {local_llm.model}")
        print(f"📡 Base URL: {local_llm.base_url}")

        # Test a simple call (without CrewAI imports to avoid other issues)
        print("\n🧪 Testing simple StreamingLLM call...")
        messages = [{"role": "user", "content": "Hi"}]
        response = local_llm.call(messages, max_tokens=10)
        print(f"✅ Simple call successful: {len(response)} chars")
        print(f"📝 Preview: {response[:50]}...")

        print("\n🎉 All tests PASSED! The ImportError is fixed.")
        return True

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_main_import()
    sys.exit(0 if success else 1)