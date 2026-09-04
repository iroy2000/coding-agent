#!/usr/bin/env python3
"""
MCP Integration Test - Tests the server via JSON-RPC stdin/stdout.

This test validates that our MCP stdio server correctly implements
the protocol by sending actual MCP messages and checking responses.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path


async def test_mcp_server():
    """Test MCP server with real JSON-RPC messages."""
    
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  🧪 MCP INTEGRATION TEST                                  ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")
    
    # Start server
    print("1️⃣  Starting MCP server...")
    cmd = [
        "venv/bin/coding-agent",
        "serve",
        "--workspace", "."
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print("   ✅ Server process started (PID: {})\n".format(process.pid))
    
    # Give server time to initialize
    await asyncio.sleep(2)
    
    try:
        # Test 1: Initialize
        print("2️⃣  Sending initialize request...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        request_line = json.dumps(init_request) + "\n"
        process.stdin.write(request_line.encode())
        await process.stdin.drain()
        
        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=5.0
            )
            
            if response_line:
                init_response = json.loads(response_line.decode())
                
                if "result" in init_response:
                    server_info = init_response["result"]["serverInfo"]
                    print(f"   ✅ Initialize successful!")
                    print(f"      Server: {server_info['name']} v{server_info['version']}\n")
                else:
                    print(f"   ❌ Initialize failed: {init_response.get('error', 'Unknown error')}\n")
                    return False
            else:
                print("   ❌ No response received\n")
                return False
                
        except asyncio.TimeoutError:
            print("   ❌ Timeout waiting for response\n")
            return False
            
        # Test 2: List tools
        print("3️⃣  Sending tools/list request...")
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        request_line = json.dumps(list_request) + "\n"
        process.stdin.write(request_line.encode())
        await process.stdin.drain()
        
        try:
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=5.0
            )
            
            if response_line:
                list_response = json.loads(response_line.decode())
                
                if "result" in list_response:
                    tools = list_response["result"]["tools"]
                    print(f"   ✅ Found {len(tools)} tools:")
                    for tool in tools:
                        print(f"      • {tool['name']}")
                    print()
                else:
                    print(f"   ❌ List tools failed: {list_response.get('error', 'Unknown error')}\n")
                    return False
            else:
                print("   ❌ No response received\n")
                return False
                
        except asyncio.TimeoutError:
            print("   ❌ Timeout waiting for response\n")
            return False
            
        # Test 3: Call read_file tool
        print("4️⃣  Testing read_file tool...")
        call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {
                    "file_path": "README.md"
                }
            }
        }
        
        request_line = json.dumps(call_request) + "\n"
        process.stdin.write(request_line.encode())
        await process.stdin.drain()
        
        try:
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=5.0
            )
            
            if response_line:
                call_response = json.loads(response_line.decode())
                
                if "result" in call_response:
                    content = call_response["result"]["content"]
                    if content and len(content) > 0:
                        text = content[0]["text"]
                        lines = text.split("\n")
                        print(f"   ✅ Read file successful!")
                        print(f"      File: README.md")
                        print(f"      Lines: {len(lines)}")
                        print(f"      Preview: {lines[0][:60]}...\n")
                    else:
                        print("   ❌ Empty content received\n")
                        return False
                else:
                    print(f"   ❌ Tool call failed: {call_response.get('error', 'Unknown error')}\n")
                    return False
            else:
                print("   ❌ No response received\n")
                return False
                
        except asyncio.TimeoutError:
            print("   ❌ Timeout waiting for response\n")
            return False
            
        print("="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\n✅ MCP stdio protocol is working correctly")
        print("✅ Server handles initialize, list, and tool calls")
        print("✅ Ready for Claude Desktop integration\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up
        print("5️⃣  Stopping server...")
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=3.0)
            print("   ✅ Server stopped cleanly\n")
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            print("   ⚠️  Server force-killed\n")


async def main():
    """Run the integration test."""
    try:
        success = await test_mcp_server()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
