#!/usr/bin/env python3
"""
Test script for StreamingLLM tool support
"""

from core.llm_streaming_client import StreamingLLM

def test_streaming_llm_with_tools():
    """Test the StreamingLLM class with tool support"""
    print("🧪 Testing StreamingLLM with tools...")

    # Create StreamingLLM instance
    llm = StreamingLLM(
        model_name="Qwen3-4B-Q5_K_M",
        base_url="http://localhost:5020/v1"
    )

    # Test messages with tool schema
    messages = [
        {"role": "system", "content": "You are a helpful assistant with access to tools."},
        {"role": "user", "content": "Check the Bitwarden vault status."}
    ]

    # Mock tool schema (simplified version of what CrewAI sends)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "autonomous_bitwarden_cli",
                "description": "Führt Bitwarden-CLI-Befehle aus.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "CLI command to execute"}
                    },
                    "required": ["command"]
                }
            }
        }
    ]

    print(f"🤖 Model: {llm.model}")
    print(f"🛠️ Function calling supported: {llm.supports_function_calling()}")
    print(f"🔧 Number of tools: {len(tools)}")

    # Test call with tools
    try:
        response = llm.call(messages, tools=tools, max_tokens=100)
        print(f"✅ Response type: {type(response)}")

        if isinstance(response, dict):
            print(f"📝 Content: {response.get('content', 'N/A')[:100]}...")
            print(f"🔧 Tool calls: {len(response.get('tool_calls', []))}")
            if response.get('tool_calls'):
                for i, tool_call in enumerate(response['tool_calls']):
                    print(f"  Tool {i+1}: {tool_call}")
        else:
            print(f"📝 Response: {response[:100]}...")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_streaming_llm_with_tools()
    if success:
        print("\n🎉 Tool support test PASSED!")
    else:
        print("\n💥 Tool support test FAILED!")