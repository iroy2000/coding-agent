"""Tests for Rich display rendering helpers in `utils/display.py`."""

from coding_agent.utils import display


class TestSimpleMessages:
    def test_print_user_message(self, capsys):
        display.print_user_message("hello")
        out = capsys.readouterr().out
        assert "You:" in out
        assert "hello" in out

    def test_print_agent_message(self, capsys):
        display.print_agent_message("hi there")
        out = capsys.readouterr().out
        assert "Agent:" in out
        assert "hi there" in out

    def test_print_system_message(self, capsys):
        display.print_system_message("system note")
        assert "system note" in capsys.readouterr().out

    def test_print_error_message(self, capsys):
        display.print_error_message("boom")
        out = capsys.readouterr().out
        assert "Error:" in out
        assert "boom" in out

    def test_print_success_message(self, capsys):
        display.print_success_message("done")
        assert "done" in capsys.readouterr().out


class TestFileOperation:
    def test_success_status(self, capsys):
        display.print_file_operation("Writing", "foo.py", status="success")
        out = capsys.readouterr().out
        assert "Writing" in out
        assert "foo.py" in out

    def test_error_status(self, capsys):
        display.print_file_operation("Reading", "bar.py", status="error")
        assert "bar.py" in capsys.readouterr().out

    def test_unknown_status_falls_back(self, capsys):
        display.print_file_operation("Doing", "baz.py", status="whatever")
        assert "baz.py" in capsys.readouterr().out


class TestCodeAndMarkdown:
    def test_print_code_block(self, capsys):
        display.print_code_block("print('hi')", language="python")
        out = capsys.readouterr().out
        assert "print" in out

    def test_print_markdown(self, capsys):
        display.print_markdown("# Title\n\nSome *text*")
        out = capsys.readouterr().out
        assert "Title" in out

    def test_print_panel(self, capsys):
        display.print_panel("panel body", title="My Title")
        out = capsys.readouterr().out
        assert "panel body" in out
        assert "My Title" in out

    def test_print_table(self, capsys):
        display.print_table("My Table", ["Col1", "Col2"], [["a", "b"], ["c", "d"]])
        out = capsys.readouterr().out
        assert "My Table" in out
        assert "Col1" in out


class TestSpinnerAndSeparator:
    def test_create_spinner_returns_progress(self):
        progress = display.create_spinner("Working...")
        assert progress is not None
        assert hasattr(progress, "__enter__")

    def test_print_separator_default(self, capsys):
        display.print_separator()
        out = capsys.readouterr().out
        assert "─" in out

    def test_print_separator_custom(self, capsys):
        display.print_separator(char="=", length=5)
        out = capsys.readouterr().out
        assert "=====" in out


class TestWelcomeAndHelp:
    def test_print_welcome_message(self, capsys):
        display.print_welcome_message()
        out = capsys.readouterr().out
        assert "Welcome to Coding Agent CLI" in out

    def test_print_help_message(self, capsys):
        display.print_help_message()
        out = capsys.readouterr().out
        assert "Available Commands" in out
        assert "exit, quit" in out


class TestWorkspaceInfo:
    def test_with_file_count(self, capsys):
        display.print_workspace_info("/tmp/project", file_count=42)
        out = capsys.readouterr().out
        assert "/tmp/project" in out
        assert "42" in out

    def test_without_file_count(self, capsys):
        display.print_workspace_info("/tmp/project")
        out = capsys.readouterr().out
        assert "/tmp/project" in out


class TestStreamAgentResponse:
    def test_streams_and_joins_chunks(self, capsys):
        chunks = ["Hello", ", ", "world!"]
        result = display.stream_agent_response(iter(chunks))
        assert result == "Hello, world!"
        out = capsys.readouterr().out
        assert "Hello, world!" in out

    def test_skips_empty_chunks(self, capsys):
        chunks = ["A", "", None, "B"]
        result = display.stream_agent_response(iter(chunks))
        assert result == "AB"


class TestFileList:
    def test_empty_list(self, capsys):
        display.print_file_list([])
        assert "No files found" in capsys.readouterr().out

    def test_groups_by_directory(self, capsys):
        display.print_file_list(["src/main.py", "src/utils.py", "README.md"], title="Project Files")
        out = capsys.readouterr().out
        assert "Project Files" in out
        assert "main.py" in out
        assert "README.md" in out


class TestFileContent:
    def test_auto_detects_language(self, capsys):
        display.print_file_content("print('hi')\n", "script.py")
        out = capsys.readouterr().out
        assert "script.py" in out

    def test_truncates_with_max_lines(self, capsys):
        content = "\n".join(f"line{i}" for i in range(10))
        display.print_file_content(content, "file.txt", max_lines=3)
        out = capsys.readouterr().out
        assert "more lines" in out

    def test_unknown_extension_defaults_to_text(self, capsys):
        display.print_file_content("some data", "file.unknownext")
        out = capsys.readouterr().out
        assert "file.unknownext" in out


class TestFileOperationResult:
    def test_success(self, capsys):
        display.print_file_operation_result(True, "wrote file", operation="Write")
        out = capsys.readouterr().out
        assert "Write:" in out
        assert "wrote file" in out

    def test_failure(self, capsys):
        display.print_file_operation_result(False, "permission denied", operation="Write")
        out = capsys.readouterr().out
        assert "Write failed:" in out
        assert "permission denied" in out
