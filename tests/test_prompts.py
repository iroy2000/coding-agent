"""Tests for coding_agent.llm.prompts."""

from coding_agent.llm.prompts import (
    EXAMPLE_INTERACTIONS,
    get_chat_prompt,
    get_code_generation_prompt,
    get_code_review_prompt,
    get_debugging_prompt,
    get_example_interaction,
    get_explanation_prompt,
    get_file_operation_instruction,
    get_refactoring_prompt,
    get_system_prompt,
)


class TestGetSystemPrompt:
    def test_includes_workspace_path(self):
        prompt = get_system_prompt("/my/workspace")
        assert "/my/workspace" in prompt

    def test_mentions_all_commands(self):
        prompt = get_system_prompt(".")
        for command in ["READ_FILE", "LIST_FILES", "WRITE_FILE", "EDIT_FILE", "RUN_COMMAND"]:
            assert command in prompt

    def test_returns_string(self):
        assert isinstance(get_system_prompt("."), str)


class TestGetChatPrompt:
    def test_without_context_returns_message_only(self):
        result = get_chat_prompt("Hello there")
        assert result == "Hello there"

    def test_with_context_includes_both(self):
        result = get_chat_prompt("Hello there", context="some file context")
        assert "some file context" in result
        assert "Hello there" in result
        assert result.index("some file context") < result.index("Hello there")

    def test_with_none_context_behaves_like_no_context(self):
        result = get_chat_prompt("msg", context=None)
        assert result == "msg"


class TestGetCodeGenerationPrompt:
    def test_includes_description(self):
        result = get_code_generation_prompt("a fibonacci function")
        assert "a fibonacci function" in result

    def test_includes_language_when_given(self):
        result = get_code_generation_prompt("a sort function", language="Python")
        assert "in Python" in result

    def test_omits_language_hint_when_not_given(self):
        result = get_code_generation_prompt("a sort function")
        assert " in " not in result.split("\n")[0] or "based on the following" in result


class TestGetCodeReviewPrompt:
    def test_includes_code(self):
        result = get_code_review_prompt("def foo(): pass")
        assert "def foo(): pass" in result

    def test_includes_focus_when_given(self):
        result = get_code_review_prompt("def foo(): pass", focus="security")
        assert "Focus on: security" in result

    def test_no_focus_line_when_not_given(self):
        result = get_code_review_prompt("def foo(): pass")
        assert "Focus on:" not in result


class TestGetRefactoringPrompt:
    def test_includes_code_and_goal(self):
        result = get_refactoring_prompt("def foo(): pass", "improve readability")
        assert "def foo(): pass" in result
        assert "improve readability" in result


class TestGetDebuggingPrompt:
    def test_includes_code_and_error(self):
        result = get_debugging_prompt("x = 1/0", "ZeroDivisionError")
        assert "x = 1/0" in result
        assert "ZeroDivisionError" in result

    def test_includes_context_when_given(self):
        result = get_debugging_prompt("x = 1/0", "ZeroDivisionError", context="happens on startup")
        assert "happens on startup" in result

    def test_no_context_section_when_not_given(self):
        result = get_debugging_prompt("x = 1/0", "ZeroDivisionError")
        assert "Additional Context:" not in result


class TestGetExplanationPrompt:
    def test_includes_code(self):
        result = get_explanation_prompt("def foo(): pass")
        assert "def foo(): pass" in result

    def test_default_detail_level_is_medium(self):
        default_result = get_explanation_prompt("code")
        medium_result = get_explanation_prompt("code", detail_level="medium")
        assert default_result == medium_result

    def test_brief_detail_level(self):
        result = get_explanation_prompt("code", detail_level="brief")
        assert "brief, high-level" in result

    def test_detailed_detail_level(self):
        result = get_explanation_prompt("code", detail_level="detailed")
        assert "line-by-line" in result

    def test_unknown_detail_level_falls_back_to_medium(self):
        result = get_explanation_prompt("code", detail_level="nonsense")
        medium_result = get_explanation_prompt("code", detail_level="medium")
        assert result == medium_result


class TestGetFileOperationInstruction:
    def test_read_file_without_content(self):
        result = get_file_operation_instruction("READ_FILE", "main.py")
        assert "ACTION: READ_FILE" in result
        assert "PATH: main.py" in result
        assert "CONTENT:" not in result

    def test_write_file_with_content(self):
        result = get_file_operation_instruction("WRITE_FILE", "main.py", content="print(1)")
        assert "ACTION: WRITE_FILE" in result
        assert "PATH: main.py" in result
        assert "CONTENT:\nprint(1)" in result

    def test_edit_file_with_content(self):
        result = get_file_operation_instruction("EDIT_FILE", "main.py", content="diff text")
        assert "CONTENT:\ndiff text" in result

    def test_content_ignored_for_read_and_list(self):
        result = get_file_operation_instruction("READ_FILE", "main.py", content="ignored")
        assert "ignored" not in result

        result = get_file_operation_instruction("LIST_FILES", ".", content="ignored")
        assert "ignored" not in result


class TestGetExampleInteraction:
    def test_returns_known_example(self):
        assert get_example_interaction("file_read") == EXAMPLE_INTERACTIONS["file_read"]
        assert get_example_interaction("file_write") == EXAMPLE_INTERACTIONS["file_write"]
        assert get_example_interaction("code_explanation") == EXAMPLE_INTERACTIONS["code_explanation"]

    def test_returns_none_for_unknown_example(self):
        assert get_example_interaction("does-not-exist") is None
