# Contributing to Coding Agent CLI

Thanks for taking a look. This is a small, mostly solo-maintained project, so contributions of any size — a bug report, a typo fix, a real feature — are genuinely useful.

## Contents

1. [Ground rules](#ground-rules)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [How to Contribute](#how-to-contribute)
5. [Coding Standards](#coding-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Commit Messages](#commit-messages)
8. [Pull Request Process](#pull-request-process)

---

## Ground rules

Be respectful, assume good faith, and keep feedback about the code, not the person. Harassment or personal attacks aren't tolerated. That's it — this isn't a large enough project to need much more than that.

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Ollama (for testing LLM features)
- Basic understanding of Python and CLI applications

### Project Overview

Coding Agent CLI is structured as follows:

```
src/coding_agent/
├── cli.py              # Command-line interface (Typer)
├── agent.py            # Core agent logic
├── llm/                # LLM integration
│   ├── ollama_client.py
│   └── prompts.py
├── tools/              # File operations
│   └── file_manager.py
├── storage/            # History management
│   └── history.py
└── utils/              # Utilities
    ├── config.py
    └── display.py
```

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/coding-agent.git
cd coding-agent
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
pip install -e ".[dev]"
```

This installs:
- The package in editable mode
- Development dependencies (pytest, black, ruff, mypy)
- All runtime dependencies

### 4. Verify Installation

```bash
# Run tests
pytest

# Check code style
black --check src/ tests/
ruff check src/ tests/

# Type checking
mypy src/
```

### 5. Setup Pre-commit Hooks (Optional but Recommended)

```bash
pip install pre-commit
pre-commit install
```

---

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. Check existing issues to avoid duplicates
2. Collect relevant information (OS, Python version, error messages)

When creating a bug report, include:
- **Title**: Clear, descriptive summary
- **Description**: Detailed explanation of the issue
- **Steps to Reproduce**: Numbered list of exact steps
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python version, Ollama version
- **Logs**: Relevant error messages or logs

**Example:**
```markdown
### Bug: Chat command fails with permission error

**Description:** When running `coding-agent chat` in a read-only directory, the command fails with a permission error.

**Steps to Reproduce:**
1. Navigate to a read-only directory
2. Run `coding-agent chat`
3. Try to create a file

**Expected:** Should show a clear error message about permissions
**Actual:** Shows confusing stack trace

**Environment:**
- OS: macOS 14.0
- Python: 3.11.4
- Version: 1.0.0

**Error Message:**
```
PermissionError: [Errno 13] Permission denied: '.coding-agent'
```
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. Include:
- **Clear title** describing the enhancement
- **Detailed description** of the proposed feature
- **Use cases** explaining why this would be useful
- **Possible implementation** if you have ideas
- **Examples** of similar features in other tools

### Your First Code Contribution

Unsure where to start? Look for issues labeled:
- `good first issue` - Easy issues for beginners
- `help wanted` - Issues that need contributors
- `documentation` - Documentation improvements

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with these tools:

#### Code Formatting with Black
```bash
# Format all code
black src/ tests/

# Check without modifying
black --check src/ tests/
```

#### Linting with Ruff
```bash
# Run linter
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/
```

#### Type Checking with MyPy
```bash
mypy src/
```

### Code Style Requirements

#### 1. Type Hints
Always use type hints for function parameters and return values:

```python
# Good
def process_file(file_path: str, mode: str = "r") -> dict:
    """Process a file and return metadata."""
    ...

# Avoid
def process_file(file_path, mode="r"):
    ...
```

#### 2. Docstrings
Use Google-style docstrings:

```python
def calculate_total(items: List[Dict], tax_rate: float) -> float:
    """
    Calculate total price including tax.
    
    Args:
        items: List of items with 'price' and 'quantity' keys
        tax_rate: Tax rate as decimal (e.g., 0.08 for 8%)
        
    Returns:
        Total price including tax
        
    Raises:
        ValueError: If items is empty or tax_rate is negative
        
    Examples:
        >>> items = [{'price': 10.0, 'quantity': 2}]
        >>> calculate_total(items, 0.08)
        21.6
    """
    ...
```

#### 3. Error Handling
Be explicit with error handling:

```python
# Good
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise CustomException("User-friendly message") from e

# Avoid
try:
    result = risky_operation()
except:
    pass
```

#### 4. Import Organization
```python
# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import typer
from rich.console import Console

# Local imports
from coding_agent.tools import FileManager
from coding_agent.utils import display
```

---

## Testing Guidelines

### Test Requirements

All code contributions must include tests:
- New features require new tests
- Bug fixes require regression tests
- Aim for 80%+ coverage on new code

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file_manager.py

# Run with coverage
pytest --cov=src/coding_agent --cov-report=html

# Run specific test
pytest tests/test_file_manager.py::TestFileManager::test_read_file
```

### Writing Tests

#### Test Structure
```python
import pytest
from coding_agent.tools.file_manager import FileManager

class TestFileManager:
    """Tests for FileManager class."""
    
    def test_read_file_success(self, temp_dir):
        """Test reading an existing file."""
        # Arrange
        fm = FileManager(workspace_path=str(temp_dir))
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")
        
        # Act
        success, content = fm.read_file("test.txt")
        
        # Assert
        assert success is True
        assert content == "Hello, World!"
    
    def test_read_file_not_found(self, temp_dir):
        """Test reading a non-existent file."""
        fm = FileManager(workspace_path=str(temp_dir))
        
        success, error = fm.read_file("nonexistent.txt")
        
        assert success is False
        assert "not found" in error.lower()
```

#### Using Fixtures
```python
@pytest.fixture
def sample_workspace(temp_dir):
    """Create a sample workspace with files."""
    (temp_dir / "src").mkdir()
    (temp_dir / "src" / "main.py").write_text("print('hello')")
    (temp_dir / "README.md").write_text("# Test")
    return temp_dir
```

#### Mocking External Dependencies
```python
from unittest.mock import Mock, patch

@patch('coding_agent.llm.ollama_client.ollama.Client')
def test_generate_response(mock_client_class):
    """Test LLM response generation."""
    # Setup mock
    mock_client = Mock()
    mock_client.chat.return_value = {
        "message": {"content": "Test response"}
    }
    mock_client_class.return_value = mock_client
    
    # Test
    client = OllamaClient()
    response = client.generate("Test prompt")
    
    assert response == "Test response"
```

---

## Commit Messages

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(cli): add export command for conversation history

Implement new command to export conversation history to JSON, TXT, or
Markdown formats. Includes support for specifying output file and format.

Closes #42
```

```
fix(history): prevent session ID collision

Add microseconds to session ID format to prevent collisions when creating
multiple sessions rapidly. Changed format from %Y%m%d_%H%M%S to
%Y%m%d_%H%M%S_%f.

Fixes #38
```

```
docs: add comprehensive usage guide

Create detailed USAGE_GUIDE.md with examples for all commands, troubleshooting
section, and best practices.
```

### Best Practices

- Use present tense ("add feature" not "added feature")
- Use imperative mood ("move cursor" not "moves cursor")
- First line should be 50 characters or less
- Body should wrap at 72 characters
- Reference issues and pull requests

---

## Pull Request Process

### Before Submitting

1. **Update your fork:**
   ```bash
   git remote add upstream https://github.com/iroy2000/coding-agent.git
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create a feature branch:**
   ```bash
   git checkout -b feature/my-new-feature
   ```

3. **Make your changes:**
   - Write code following coding standards
   - Add/update tests
   - Update documentation
   - Run tests locally

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

5. **Push to your fork:**
   ```bash
   git push origin feature/my-new-feature
   ```

### Creating a Pull Request

1. Go to the repository on GitHub
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill out the PR template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Updated existing tests

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed my code
- [ ] Commented complex sections
- [ ] Updated documentation
- [ ] No new warnings
- [ ] Added tests with good coverage

## Related Issues
Fixes #(issue number)
```

### Review Process

1. **Automated checks** run on your PR
2. **Maintainer reviews** your code
3. **Address feedback** if requested
4. **Merge** once approved

### After Your PR is Merged

1. Delete your feature branch:
   ```bash
   git branch -d feature/my-new-feature
   git push origin --delete feature/my-new-feature
   ```

2. Update your main branch:
   ```bash
   git checkout main
   git pull upstream main
   ```

---

## Development Tips

### Running in Development Mode

```bash
# Install in editable mode
pip install -e .

# Now changes to code are immediately available
coding-agent chat
```

### Debugging

```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use debugger
import pdb; pdb.set_trace()

# Or use Rich's inspect
from rich import inspect
inspect(my_object)
```

### Testing with Different Models

```bash
# Test with small model
coding-agent config --set OLLAMA_MODEL=codellama:7b-code

# Test with large model
coding-agent config --set OLLAMA_MODEL=codellama:34b
```

---

## Project Roadmap

Current and planned work is tracked in [GitHub Issues](https://github.com/iroy2000/coding-agent/issues), not a separate planning doc.

---

## Getting Help

- [Usage Guide](USAGE_GUIDE.md)
- [Issues](https://github.com/iroy2000/coding-agent/issues) for bugs and feature requests

---

Thanks for reading this far — even fixing a typo helps.
