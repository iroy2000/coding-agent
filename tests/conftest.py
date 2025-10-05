"""Pytest configuration and fixtures for testing."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_workspace(temp_dir: Path) -> Path:
    """Create a sample workspace with test files."""
    # Create directory structure
    (temp_dir / "src").mkdir()
    (temp_dir / "tests").mkdir()
    (temp_dir / "docs").mkdir()
    
    # Create sample files
    (temp_dir / "README.md").write_text("# Test Project\n\nThis is a test.")
    (temp_dir / ".gitignore").write_text("*.pyc\n__pycache__\n.env\n")
    
    # Python files
    (temp_dir / "src" / "__init__.py").write_text("")
    (temp_dir / "src" / "main.py").write_text(
        "def main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()\n"
    )
    (temp_dir / "src" / "utils.py").write_text(
        "def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n"
    )
    
    # Test files
    (temp_dir / "tests" / "__init__.py").write_text("")
    (temp_dir / "tests" / "test_main.py").write_text(
        "def test_example():\n    assert True\n"
    )
    
    # Documentation
    (temp_dir / "docs" / "guide.md").write_text("# User Guide\n\nHow to use this project.")
    
    return temp_dir


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        "model": "codellama:latest",
        "response": "This is a test response from the AI assistant.",
        "done": True,
    }


@pytest.fixture
def sample_file_content():
    """Sample file content for testing."""
    return """def calculate_sum(numbers):
    '''Calculate the sum of a list of numbers.'''
    total = 0
    for num in numbers:
        total += num
    return total


def calculate_average(numbers):
    '''Calculate the average of a list of numbers.'''
    if not numbers:
        return 0
    return calculate_sum(numbers) / len(numbers)
"""


@pytest.fixture
def sample_history_session():
    """Sample conversation history session."""
    return {
        "session_id": "20250101_120000",
        "created_at": "2025-01-01T12:00:00",
        "workspace_path": "/test/workspace",
        "model": "codellama:latest",
        "messages": [
            {
                "role": "user",
                "content": "Hello, can you help me?",
                "timestamp": "2025-01-01T12:00:05"
            },
            {
                "role": "assistant",
                "content": "Of course! I'd be happy to help. What do you need assistance with?",
                "timestamp": "2025-01-01T12:00:10"
            },
            {
                "role": "user",
                "content": "Create a Python function to calculate factorial",
                "timestamp": "2025-01-01T12:00:20"
            },
            {
                "role": "assistant",
                "content": "Here's a factorial function:\n\ndef factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
                "timestamp": "2025-01-01T12:00:25"
            }
        ]
    }
