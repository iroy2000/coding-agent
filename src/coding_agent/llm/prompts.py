"""System prompts and prompt templates for the coding agent."""

from typing import Optional


def get_system_prompt(workspace_path: str) -> str:
    """
    Get the system prompt for the coding agent.

    Args:
        workspace_path: Path to the current workspace

    Returns:
        System prompt string
    """
    return f"""You are a helpful coding assistant with full access to the user's workspace at: {workspace_path}

You MUST use these exact commands when you need to perform file operations:

READ_FILE: path/to/file
  - Use this to read any file in the workspace
  
LIST_FILES: path/to/directory
  - Use this to list files in a directory

WRITE_FILE: path/to/file
CONTENT:
```language
file content here
```
  - Use this to create or overwrite a file

EDIT_FILE: path/to/file
OLD:
```
text to replace
```
NEW:
```
replacement text
```
  - Use this to edit existing files

IMPORTANT RULES:
1. When a user asks you to read, write, list, or edit files, you MUST use these commands
2. Use the EXACT format shown above - the parser is looking for these patterns
3. You can include explanations before or after the commands
4. Multiple commands can be in one response

Example response when user asks "read the config file":
"I'll read the configuration file for you.

READ_FILE: config.py

Let me check what's in there."

Example response when user asks "create a hello.py file":
"I'll create a hello.py file for you.

WRITE_FILE: hello.py
CONTENT:
```python
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
```

The file has been created with a simple hello world program."

Now respond naturally to the user while using these commands when needed."""


def get_chat_prompt(user_message: str, context: Optional[str] = None) -> str:
    """
    Format a user message with optional context.

    Args:
        user_message: The user's message
        context: Optional context about files or workspace

    Returns:
        Formatted prompt
    """
    if context:
        return f"""Context:
{context}

User Request:
{user_message}"""
    return user_message


def get_code_generation_prompt(description: str, language: Optional[str] = None) -> str:
    """
    Create a prompt for code generation.

    Args:
        description: Description of what to generate
        language: Programming language (optional)

    Returns:
        Formatted prompt
    """
    lang_hint = f" in {language}" if language else ""
    return f"""Generate code{lang_hint} based on the following description:

{description}

Please provide:
1. Clean, well-commented code
2. Explanation of the approach
3. Any important considerations or gotchas"""


def get_code_review_prompt(code: str, focus: Optional[str] = None) -> str:
    """
    Create a prompt for code review.

    Args:
        code: Code to review
        focus: Specific aspect to focus on (e.g., "security", "performance")

    Returns:
        Formatted prompt
    """
    focus_text = f"\nFocus on: {focus}" if focus else ""
    return f"""Please review the following code:{focus_text}

```
{code}
```

Provide:
1. Overall assessment
2. Potential issues or bugs
3. Suggestions for improvement
4. Best practices that could be applied"""


def get_refactoring_prompt(code: str, goal: str) -> str:
    """
    Create a prompt for code refactoring.

    Args:
        code: Code to refactor
        goal: Refactoring goal (e.g., "use async/await", "improve readability")

    Returns:
        Formatted prompt
    """
    return f"""Please refactor the following code to: {goal}

Current code:
```
{code}
```

Provide:
1. The refactored code
2. Explanation of changes made
3. Benefits of the refactoring"""


def get_debugging_prompt(code: str, error: str, context: Optional[str] = None) -> str:
    """
    Create a prompt for debugging assistance.

    Args:
        code: Code with the issue
        error: Error message or description
        context: Additional context about the problem

    Returns:
        Formatted prompt
    """
    context_text = f"\nAdditional Context:\n{context}" if context else ""
    return f"""Help debug the following issue:

Error: {error}

Code:
```
{code}
```{context_text}

Please provide:
1. Root cause analysis
2. Suggested fix
3. Explanation of why the error occurred
4. How to prevent similar issues"""


def get_explanation_prompt(code: str, detail_level: str = "medium") -> str:
    """
    Create a prompt for code explanation.

    Args:
        code: Code to explain
        detail_level: Level of detail ("brief", "medium", "detailed")

    Returns:
        Formatted prompt
    """
    detail_instructions = {
        "brief": "Provide a brief, high-level explanation.",
        "medium": "Provide a clear explanation of what the code does and how.",
        "detailed": "Provide a detailed, line-by-line explanation including edge cases and nuances."
    }
    
    instruction = detail_instructions.get(detail_level, detail_instructions["medium"])
    
    return f"""Explain the following code. {instruction}

```
{code}
```"""


def get_file_operation_instruction(action: str, path: str, content: Optional[str] = None) -> str:
    """
    Format a file operation instruction.

    Args:
        action: Action to perform (READ_FILE, WRITE_FILE, EDIT_FILE, LIST_FILES)
        path: File or directory path
        content: Content for write operations

    Returns:
        Formatted instruction
    """
    instruction = f"ACTION: {action}\nPATH: {path}"
    
    if content and action in ["WRITE_FILE", "EDIT_FILE"]:
        instruction += f"\nCONTENT:\n{content}"
    
    return instruction


# Common coding patterns and examples
EXAMPLE_INTERACTIONS = {
    "file_read": """User: Read the config.py file
Agent: I'll read the configuration file for you.

ACTION: READ_FILE
PATH: config.py

[After reading]
The config.py file contains the application configuration...""",

    "file_write": """User: Create a new utils.py file with a helper function
Agent: I'll create a utils.py file with a helper function.

ACTION: WRITE_FILE
PATH: utils.py
CONTENT:
```python
def format_timestamp(timestamp):
    \"\"\"Format a timestamp to readable string.\"\"\"
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")
```

I've created utils.py with a timestamp formatting helper function.""",

    "code_explanation": """User: Explain what this function does
Agent: This function implements a binary search algorithm. It takes a sorted list and a target value, then efficiently finds the target's index by repeatedly dividing the search space in half..."""
}


def get_example_interaction(example_type: str) -> Optional[str]:
    """
    Get an example interaction for few-shot prompting.

    Args:
        example_type: Type of example to retrieve

    Returns:
        Example interaction string or None
    """
    return EXAMPLE_INTERACTIONS.get(example_type)
