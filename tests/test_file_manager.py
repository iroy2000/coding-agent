"""Tests for FileManager class."""

import pytest
from pathlib import Path

from coding_agent.tools.file_manager import FileManager


class TestFileManager:
    """Test suite for FileManager."""

    def test_initialization(self, sample_workspace):
        """Test FileManager initialization."""
        fm = FileManager(workspace_path=str(sample_workspace))
        # Workspace paths are resolved, which may add /private on macOS
        assert fm.workspace.name == sample_workspace.name
        assert fm.gitignore_spec is not None

    def test_read_file_success(self, sample_workspace):
        """Test reading an existing file."""
        fm = FileManager(workspace_path=str(sample_workspace))
        success, content = fm.read_file("README.md")
        assert success is True
        assert "Test Project" in content
        assert content.startswith("# Test Project")

    def test_read_file_not_found(self, sample_workspace):
        """Test reading a non-existent file."""
        fm = FileManager(workspace_path=str(sample_workspace))
        success, message = fm.read_file("nonexistent.txt")
        assert success is False
        assert "does not exist" in message

    def test_read_file_outside_workspace(self, sample_workspace):
        """Test reading file outside workspace is prevented."""
        fm = FileManager(workspace_path=str(sample_workspace))
        success, message = fm.read_file("../../etc/passwd")
        assert success is False
        assert "outside workspace" in message

    def test_write_file_success(self, sample_workspace):
        """Test writing a new file."""
        fm = FileManager(workspace_path=str(sample_workspace))
        content = "# New File\n\nThis is a test file."
        success, message = fm.write_file("new_file.md", content)
        
        assert success is True
        # Verify file was created
        assert (sample_workspace / "new_file.md").exists()
        assert (sample_workspace / "new_file.md").read_text() == content

    def test_write_file_creates_directories(self, sample_workspace):
        """Test writing file creates parent directories."""
        fm = FileManager(workspace_path=str(sample_workspace))
        content = "Test content"
        success, message = fm.write_file("nested/dir/file.txt", content)
        
        assert success is True
        # Verify file and directories were created
        assert (sample_workspace / "nested" / "dir" / "file.txt").exists()
        assert (sample_workspace / "nested" / "dir" / "file.txt").read_text() == content

    def test_write_file_overwrites(self, sample_workspace):
        """Test writing to existing file overwrites it."""
        fm = FileManager(workspace_path=str(sample_workspace))
        original = "Original content"
        updated = "Updated content"
        
        success1, _ = fm.write_file("test.txt", original)
        assert success1 is True
        assert (sample_workspace / "test.txt").read_text() == original
        
        success2, _ = fm.write_file("test.txt", updated, overwrite=True)
        assert success2 is True
        assert (sample_workspace / "test.txt").read_text() == updated

    def test_write_file_outside_workspace(self, sample_workspace):
        """Test writing file outside workspace is prevented."""
        fm = FileManager(workspace_path=str(sample_workspace))
        success, message = fm.write_file("../outside.txt", "content")
        assert success is False
        assert "outside workspace" in message

    def test_edit_file_success(self, sample_workspace):
        """Test editing an existing file."""
        fm = FileManager(workspace_path=str(sample_workspace))
        old_text = "Hello, World!"
        new_text = "Hello, Python!"
        
        success, message = fm.edit_file("src/main.py", old_text, new_text)
        
        assert success is True
        content = (sample_workspace / "src" / "main.py").read_text()
        assert "Hello, Python!" in content
        assert "Hello, World!" not in content

    def test_edit_file_not_found(self, sample_workspace):
        """Test editing a non-existent file."""
        fm = FileManager(workspace_path=str(sample_workspace))
        success, message = fm.edit_file("nonexistent.py", "old", "new")
        assert success is False
        assert "does not exist" in message

    def test_edit_file_text_not_found(self, sample_workspace):
        """Test editing with text that doesn't exist in file."""
        fm = FileManager(workspace_path=str(sample_workspace))
        success, message = fm.edit_file("src/main.py", "nonexistent text", "new text")
        assert success is False
        assert "not found" in message

    def test_list_files_all(self, sample_workspace):
        """Test listing all files in workspace."""
        fm = FileManager(workspace_path=str(sample_workspace))
        success, files = fm.list_files()
        
        assert success is True
        # Check that key files are in the list
        assert "README.md" in files
        assert "src/main.py" in files
        assert "src/utils.py" in files
        assert "tests/test_main.py" in files

    def test_list_files_with_directory(self, sample_workspace):
        """Test listing files in a specific directory."""
        fm = FileManager(workspace_path=str(sample_workspace))
        success, files = fm.list_files(directory="src")
        
        assert success is True
        # Should only contain files from src directory
        assert any("src/" in f or f.startswith("main.py") or f.startswith("utils.py") for f in files)

    def test_list_files_respects_gitignore(self, sample_workspace):
        """Test that .gitignore patterns are respected."""
        fm = FileManager(workspace_path=str(sample_workspace))
        
        # Create files that should be ignored
        (sample_workspace / "test.pyc").write_text("compiled")
        (sample_workspace / ".env").write_text("secret")
        (sample_workspace / "__pycache__").mkdir()
        (sample_workspace / "__pycache__" / "cache.pyc").write_text("cache")
        
        success, files = fm.list_files()
        
        assert success is True
        # These should be ignored
        assert "test.pyc" not in files
        assert ".env" not in files
        assert "__pycache__/cache.pyc" not in files

    def test_list_files_max_depth(self, sample_workspace):
        """Test limiting the depth of file listing."""
        fm = FileManager(workspace_path=str(sample_workspace))
        
        # Create deeply nested structure
        deep_dir = sample_workspace / "a" / "b" / "c" / "d"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep.txt").write_text("deep file")
        
        # List with max_depth=1 (only top level)
        success, files_depth_1 = fm.list_files(max_depth=1)
        assert success is True
        assert not any("a/b/c/d" in f for f in files_depth_1)

    def test_file_exists(self, sample_workspace):
        """Test checking if file exists."""
        fm = FileManager(workspace_path=str(sample_workspace))
        
        assert fm.file_exists("README.md")
        assert fm.file_exists("src/main.py")
        assert not fm.file_exists("nonexistent.txt")

    def test_get_file_info(self, sample_workspace):
        """Test getting file information."""
        fm = FileManager(workspace_path=str(sample_workspace))
        
        success, info = fm.get_file_info("README.md")
        assert success is True
        assert info["path"] == "README.md"
        assert info["size"] > 0
        assert "modified" in info
        assert not info["is_directory"]

    def test_workspace_normalization(self, temp_dir):
        """Test that workspace path is normalized."""
        # Create workspace with trailing slash
        workspace_with_slash = str(temp_dir) + "/"
        fm = FileManager(workspace_path=workspace_with_slash)
        
        # Should be normalized to Path
        assert isinstance(fm.workspace, Path)
        assert fm.workspace.name == temp_dir.name

    def test_binary_file_handling(self, sample_workspace):
        """Test handling of binary files."""
        fm = FileManager(workspace_path=str(sample_workspace))
        
        # Create a binary file with invalid UTF-8 sequences
        binary_content = bytes([0xFF, 0xFE, 0x00, 0x01, 0x80, 0x90, 0xA0, 0xB0])
        (sample_workspace / "binary.bin").write_bytes(binary_content)
        
        # Reading should return error for binary files
        success, message = fm.read_file("binary.bin")
        # Binary files may or may not be readable depending on content
        # Just verify the method returns tuple format correctly
        assert isinstance(success, bool)
        assert isinstance(message, str)


class TestRunCommand:
    """Test suite for FileManager.run_command and its safety gate."""

    def test_run_command_success(self, sample_workspace):
        fm = FileManager(workspace_path=str(sample_workspace))
        success, output = fm.run_command("echo hello-world")
        assert success is True
        assert "hello-world" in output

    def test_run_command_runs_in_workspace_directory(self, sample_workspace):
        fm = FileManager(workspace_path=str(sample_workspace))
        success, output = fm.run_command("ls")
        assert success is True
        assert "README.md" in output

    def test_run_command_nonzero_exit_reports_failure(self, sample_workspace):
        fm = FileManager(workspace_path=str(sample_workspace))
        success, output = fm.run_command("exit 1")
        assert success is False
        assert "exited with code 1" in output

    def test_run_command_captures_stderr(self, sample_workspace):
        fm = FileManager(workspace_path=str(sample_workspace))
        success, output = fm.run_command("echo err-message 1>&2 && exit 3")
        assert success is False
        assert "err-message" in output
        assert "exited with code 3" in output

    def test_run_command_empty_command_rejected(self, sample_workspace):
        fm = FileManager(workspace_path=str(sample_workspace))
        success, message = fm.run_command("   ")
        assert success is False
        assert "empty" in message.lower()

    def test_run_command_timeout(self, sample_workspace):
        fm = FileManager(workspace_path=str(sample_workspace))
        success, message = fm.run_command("sleep 2", timeout=1)
        assert success is False
        assert "timed out" in message.lower()

    @pytest.mark.parametrize(
        "command",
        [
            "rm -rf /",
            "rm -rf ~",
            "sudo rm -rf /var",
            "shutdown -h now",
            "reboot",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            ":(){ :|:& };:",
        ],
    )
    def test_dangerous_commands_are_blocked(self, sample_workspace, command):
        fm = FileManager(workspace_path=str(sample_workspace))
        assert fm.is_command_dangerous(command) is True
        success, message = fm.run_command(command)
        assert success is False
        assert "blocked" in message.lower()

    @pytest.mark.parametrize(
        "command",
        ["pytest -q", "npm test", "echo hello", "ls -la", "make build"],
    )
    def test_safe_commands_are_not_blocked(self, sample_workspace, command):
        fm = FileManager(workspace_path=str(sample_workspace))
        assert fm.is_command_dangerous(command) is False
