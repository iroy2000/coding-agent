"""Tests for coding_agent.llm.tool_schemas."""

from coding_agent.llm.tool_schemas import TOOL_DEFINITIONS, operation_name_for_tool


class TestToolDefinitions:
    """Test suite for the shared TOOL_DEFINITIONS schema list."""

    def test_defines_all_supported_operations(self):
        """Every operation understood by CodingAgent._execute_file_operation
        must have a corresponding tool definition."""
        expected_operations = {
            "READ_FILE",
            "WRITE_FILE",
            "EDIT_FILE",
            "LIST_FILES",
            "SEARCH_FILES",
            "RUN_COMMAND",
        }
        actual_operations = {
            operation_name_for_tool(tool["name"]) for tool in TOOL_DEFINITIONS
        }
        assert actual_operations == expected_operations

    def test_each_tool_has_required_schema_fields(self):
        """Each tool definition must have a name, description, and a valid
        JSON-schema `parameters` object."""
        for tool in TOOL_DEFINITIONS:
            assert isinstance(tool["name"], str) and tool["name"]
            assert isinstance(tool["description"], str) and tool["description"]
            assert tool["parameters"]["type"] == "object"
            assert "properties" in tool["parameters"]
            assert "required" in tool["parameters"]

    def test_write_file_requires_path_and_content(self):
        write_file = next(t for t in TOOL_DEFINITIONS if t["name"] == "write_file")
        assert set(write_file["parameters"]["required"]) == {"path", "content"}

    def test_edit_file_requires_path_old_and_new_text(self):
        edit_file = next(t for t in TOOL_DEFINITIONS if t["name"] == "edit_file")
        assert set(edit_file["parameters"]["required"]) == {"path", "old_text", "new_text"}


class TestOperationNameForTool:
    def test_converts_snake_case_to_upper(self):
        assert operation_name_for_tool("read_file") == "READ_FILE"
        assert operation_name_for_tool("run_command") == "RUN_COMMAND"
