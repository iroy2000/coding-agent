# Demo Documentation

This documentation was created by the FileManager.

## Features

The FileManager supports:

1. **Reading Files** - Read any text file in the workspace
2. **Writing Files** - Create new files with automatic directory creation
3. **Editing Files** - Find and replace text in existing files
4. **Listing Files** - Recursively list files with .gitignore support
5. **File Info** - Get detailed information about any file

## Code Example

```python
from coding_agent.tools.file_manager import FileManager

fm = FileManager("/path/to/workspace")
success, content = fm.read_file("example.py")
if success:
    print(content)
```

## Security

- All paths are validated to be within the workspace
- .gitignore patterns are respected
- Permission errors are handled gracefully
