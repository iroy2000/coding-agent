"""Test script for FileManager functionality."""

from coding_agent.tools.file_manager import FileManager
from coding_agent.utils.config import Config

# Load config to get workspace path
config = Config()

# Initialize FileManager
fm = FileManager(config.workspace_path)

print("Testing FileManager...")
print(f"Workspace: {fm.workspace}")
print()

# Test 1: List files
print("Test 1: List files in workspace")
success, files = fm.list_files(".", max_depth=2)
if success:
    print(f"Found {len(files)} files:")
    for f in files[:10]:  # Show first 10
        print(f"  - {f}")
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more")
else:
    print(f"Error: {files}")
print()

# Test 2: Read a file
print("Test 2: Read README.md")
success, content = fm.read_file("README.md")
if success:
    lines = content.split("\n")
    print(f"File has {len(lines)} lines")
    print("First 5 lines:")
    for line in lines[:5]:
        print(f"  {line}")
else:
    print(f"Error: {content}")
print()

# Test 3: Write a test file
print("Test 3: Write test file")
test_content = """# Test File
This is a test file created by the FileManager.

It demonstrates:
- File creation
- Directory creation (if needed)
- Content writing
"""

success, message = fm.write_file("test_output.txt", test_content, overwrite=True)
print(f"Result: {message}")
print()

# Test 4: Read the test file back
print("Test 4: Read test file back")
success, content = fm.read_file("test_output.txt")
if success:
    print("Content read successfully:")
    print(content)
else:
    print(f"Error: {content}")
print()

# Test 5: Edit the test file
print("Test 5: Edit test file")
success, message = fm.edit_file(
    "test_output.txt",
    "This is a test file",
    "This is an EDITED test file"
)
print(f"Result: {message}")
print()

# Test 6: Get file info
print("Test 6: Get file info")
success, info = fm.get_file_info("test_output.txt")
if success:
    print("File info:")
    for key, value in info.items():
        print(f"  {key}: {value}")
else:
    print(f"Error: {info}")
print()

print("All tests complete!")
