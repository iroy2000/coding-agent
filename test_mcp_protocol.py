#!/usr/bin/env python3
"""
Direct MCP Protocol Test Script

Tests the stdio_server implementation by sending JSON-RPC messages
and validating responses.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path


class MCPProtocolTester:
    """Test MCP stdio protocol directly."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.process = None
        self.request_id = 0
        
    async def start_server(self):
        """Start the MCP server process."""
        cmd = [
            "venv/bin/coding-agent",
            "serve",
            "--workspace", self.workspace_path
        ]
        
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait a bit for server to initialize
        await asyncio.sleep(1)
        
        print("✅ Server started")
        
    async def send_request(self, method: str, params: dict = None) -> dict:
        """Send a JSON-RPC request and get response."""
        self.request_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.request_id
        }
        
        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        response = json.loads(response_line.decode())
        
        return response
        
    async def test_initialize(self):
        """Test the initialize handshake."""
        print("\n📋 Test 1: Initialize")
        
        response = await self.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "protocol-tester",
                    "version": "1.0.0"
                }
            }
        )
        
        if "result" in response:
            print(f"   ✅ Initialize successful")
            print(f"   Server: {response['result']['serverInfo']['name']}")
            print(f"   Version: {response['result']['serverInfo']['version']}")
            return True
        else:
            print(f"   ❌ Initialize failed: {response.get('error')}")
            return False
            
    async def test_list_tools(self):
        """Test listing available tools."""
        print("\n📋 Test 2: List Tools")
        
        response = await self.send_request("tools/list")
        
        if "result" in response:
            tools = response["result"]["tools"]
            print(f"   ✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"      • {tool['name']}: {tool['description'][:60]}...")
            return True
        else:
            print(f"   ❌ List tools failed: {response.get('error')}")
            return False
            
    async def test_read_file(self):
        """Test the read_file tool."""
        print("\n📋 Test 3: Read File Tool")
        
        response = await self.send_request(
            "tools/call",
            {
                "name": "read_file",
                "arguments": {
                    "file_path": "README.md"
                }
            }
        )
        
        if "result" in response:
            content = response["result"]["content"][0]["text"]
            lines = content.split("\n")
            print(f"   ✅ Read file successful")
            print(f"   File: README.md")
            print(f"   Lines: {len(lines)}")
            print(f"   Preview: {lines[0][:60]}...")
            return True
        else:
            print(f"   ❌ Read file failed: {response.get('error')}")
            return False
            
    async def test_list_files(self):
        """Test the list_files tool."""
        print("\n📋 Test 4: List Files Tool")
        
        response = await self.send_request(
            "tools/call",
            {
                "name": "list_files",
                "arguments": {
                    "pattern": "*.py",
                    "max_depth": 2
                }
            }
        )
        
        if "result" in response:
            content = response["result"]["content"][0]["text"]
            files = [line for line in content.split("\n") if line.strip()]
            print(f"   ✅ List files successful")
            print(f"   Pattern: *.py")
            print(f"   Found: {len(files)} files")
            print(f"   Sample: {files[0] if files else 'none'}")
            return True
        else:
            print(f"   ❌ List files failed: {response.get('error')}")
            return False
            
    async def test_explain_code(self):
        """Test the explain_code tool."""
        print("\n📋 Test 5: Explain Code Tool")
        
        test_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        
        response = await self.send_request(
            "tools/call",
            {
                "name": "explain_code",
                "arguments": {
                    "code": test_code
                }
            }
        )
        
        if "result" in response:
            explanation = response["result"]["content"][0]["text"]
            print(f"   ✅ Explain code successful")
            print(f"   Code: fibonacci function")
            print(f"   Explanation length: {len(explanation)} chars")
            print(f"   Preview: {explanation[:100]}...")
            return True
        else:
            print(f"   ❌ Explain code failed: {response.get('error')}")
            return False
            
    async def stop_server(self):
        """Stop the MCP server."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            print("\n✅ Server stopped")
            
    async def run_all_tests(self):
        """Run all protocol tests."""
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║  🧪 MCP PROTOCOL DIRECT TESTING                           ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        
        try:
            await self.start_server()
            
            # Run tests
            results = []
            results.append(("Initialize", await self.test_initialize()))
            results.append(("List Tools", await self.test_list_tools()))
            results.append(("Read File", await self.test_read_file()))
            results.append(("List Files", await self.test_list_files()))
            results.append(("Explain Code", await self.test_explain_code()))
            
            # Summary
            print("\n" + "="*60)
            print("📊 TEST SUMMARY")
            print("="*60)
            
            passed = sum(1 for _, result in results if result)
            total = len(results)
            
            for test_name, result in results:
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{status}  {test_name}")
                
            print("="*60)
            print(f"Result: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
            
            if passed == total:
                print("\n🎉 All protocol tests passed!")
                return True
            else:
                print(f"\n⚠️  {total - passed} test(s) failed")
                return False
                
        except Exception as e:
            print(f"\n❌ Test suite failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            await self.stop_server()


async def main():
    """Run the protocol tests."""
    workspace = str(Path.cwd())
    tester = MCPProtocolTester(workspace)
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
