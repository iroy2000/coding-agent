#!/usr/bin/env python3
"""
MCP Server Startup Validation

This script validates that the MCP stdio server can:
1. Start successfully
2. Initialize the MCP SDK Server
3. Register tools correctly
4. Be ready for MCP client connections
"""

import subprocess
import sys
import time
from pathlib import Path


def test_server_startup():
    """Test that the server starts and shows correct initialization."""
    
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  ✅ MCP SERVER STARTUP VALIDATION                         ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")
    
    print("Starting MCP server with Safe Mode defaults...\n")
    
    # Start server and capture output for 3 seconds
    cmd = [
        "venv/bin/coding-agent",
        "serve",
        "--workspace", "."
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give server time to initialize
    time.sleep(3)
    
    # Check if process is still running
    if process.poll() is None:
        # Process is running, terminate it
        process.terminate()
        try:
            output, errors = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            output, errors = process.communicate()
    else:
        # Process exited
        output, errors = process.communicate()
    
    # Validate output
    print("="*60)
    print("SERVER OUTPUT:")
    print("="*60)
    if errors:
        print(errors)
    print()
    
    # Check for expected initialization messages
    checks = [
        ("MCP Server Starting", "═══ MCP Server Starting ═══" in errors),
        ("Workspace configured", "Workspace:" in errors),
        ("Safe Mode enabled", "Safe Mode:" in errors),
        ("Tools enabled", "Enabled Tools:" in errors),
        ("Server initialized", "Server initialized" in errors),
        ("read_file tool", "read_file" in errors),
        ("list_files tool", "list_files" in errors),
        ("explain_code tool", "explain_code" in errors),
        ("Server running", "Server running" in errors or process.poll() is None),
    ]
    
    print("="*60)
    print("VALIDATION CHECKS:")
    print("="*60)
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status}  {check_name}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 SUCCESS: MCP server starts correctly!")
        print("\nNext Steps:")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("1. Manual Inspector Test:")
        print("   npx @modelcontextprotocol/inspector venv/bin/coding-agent serve --workspace .")
        print()
        print("2. Claude Desktop Integration:")
        print("   Add to claude_desktop_config.json:")
        print('   {')
        print('     "mcpServers": {')
        print('       "coding-agent": {')
        print('         "command": "' + str(Path.cwd() / "venv/bin/coding-agent") + '",')
        print('         "args": ["serve", "--workspace", "/path/to/your/workspace"]')
        print('       }')
        print('     }')
        print('   }')
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return True
    else:
        print("\n❌ FAILURE: Server did not start correctly")
        print("\nDebug the errors shown above.")
        return False


if __name__ == "__main__":
    try:
        success = test_server_startup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
