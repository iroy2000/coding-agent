"""Tests for HistoryManager class."""

import json
import time
import pytest
from pathlib import Path

from coding_agent.storage.history import HistoryManager


class TestHistoryManager:
    """Test suite for HistoryManager."""

    def test_initialization(self, temp_dir):
        """Test HistoryManager initialization."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        assert hm.history_dir == history_dir
        assert history_dir.exists()

    def test_create_session(self, temp_dir):
        """Test creating a new session"""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        session_id = hm.create_session(
            workspace_path="/test/workspace",
            model="codellama:latest"
        )
        
        assert session_id is not None
        assert len(session_id) > 0
        
        # Check session file exists
        session_file = history_dir / f"session_{session_id}.json"
        assert session_file.exists()
        
        # Verify session data
        session_data = json.loads(session_file.read_text())
        assert session_data["session_id"] == session_id
        assert session_data["workspace_path"] == "/test/workspace"
        assert session_data["model"] == "codellama:latest"
        assert "created_at" in session_data
        assert session_data["messages"] == []

    def test_add_message(self, temp_dir, sample_history_session):
        """Test adding a message to a session."""
        history_dir = temp_dir / "history"
        history_dir.mkdir(parents=True)
        hm = HistoryManager(history_dir=str(history_dir))
        
        session_id = sample_history_session["session_id"]
        
        # Create session file
        session_file = history_dir / f"session_{session_id}.json"
        session_file.write_text(json.dumps({
            "session_id": session_id,
            "created_at": sample_history_session["created_at"],
            "workspace_path": sample_history_session["workspace_path"],
            "model": sample_history_session["model"],
            "messages": []
        }))
        
        # Add message
        hm.add_message(session_id, "user", "Test message")
        
        # Verify message was added
        session_data = json.loads(session_file.read_text())
        assert len(session_data["messages"]) == 1
        assert session_data["messages"][0]["role"] == "user"
        assert session_data["messages"][0]["content"] == "Test message"
        assert "timestamp" in session_data["messages"][0]

    def test_add_multiple_messages(self, temp_dir):
        """Test adding multiple messages to a session."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        session_id = hm.create_session("/test/workspace", "codellama:latest")
        
        # Add multiple messages
        hm.add_message(session_id, "user", "First message")
        hm.add_message(session_id, "assistant", "First response")
        hm.add_message(session_id, "user", "Second message")
        hm.add_message(session_id, "assistant", "Second response")
        
        # Load and verify
        session_data = hm.load_session(session_id)
        assert len(session_data["messages"]) == 4
        assert session_data["messages"][0]["content"] == "First message"
        assert session_data["messages"][3]["content"] == "Second response"

    def test_load_session(self, temp_dir, sample_history_session):
        """Test loading a session."""
        history_dir = temp_dir / "history"
        history_dir.mkdir(parents=True)
        hm = HistoryManager(history_dir=str(history_dir))
        
        session_id = sample_history_session["session_id"]
        session_file = history_dir / f"session_{session_id}.json"
        session_file.write_text(json.dumps(sample_history_session))
        
        # Load session
        loaded = hm.load_session(session_id)
        
        assert loaded is not None
        assert loaded["session_id"] == session_id
        assert len(loaded["messages"]) == 4
        assert loaded["model"] == "codellama:latest"

    def test_load_nonexistent_session(self, temp_dir):
        """Test loading a session that doesn't exist."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        loaded = hm.load_session("nonexistent_20250101_120000")
        assert loaded is None

    def test_list_sessions_empty(self, temp_dir):
        """Test listing sessions when none exist."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        sessions = hm.list_sessions()
        assert sessions == []

    def test_list_sessions(self, temp_dir):
        """Test listing multiple sessions."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        # Create multiple sessions
        session1 = hm.create_session("/workspace1", "model1")
        hm.add_message(session1, "user", "Hello")
        
        time.sleep(0.01)  # Ensure distinct modification times
        
        session2 = hm.create_session("/workspace2", "model2")
        hm.add_message(session2, "user", "Hi")
        hm.add_message(session2, "assistant", "Hello!")
        
        # List sessions
        sessions = hm.list_sessions()
        
        assert len(sessions) == 2
        assert any(s["session_id"] == session1 for s in sessions)
        assert any(s["session_id"] == session2 for s in sessions)
        
        # Check message counts
        for session in sessions:
            if session["session_id"] == session1:
                assert session["message_count"] == 1
            elif session["session_id"] == session2:
                assert session["message_count"] == 2

    def test_list_sessions_with_limit(self, temp_dir):
        """Test listing sessions with a limit."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        # Create 5 sessions with distinct modification times
        for i in range(5):
            hm.create_session(f"/workspace{i}", "model")
            time.sleep(0.01)  # Ensure distinct modification times
        
        # List with limit
        sessions = hm.list_sessions(limit=3)
        assert len(sessions) == 3

    def test_list_sessions_filtered_by_workspace(self, temp_dir):
        """Test listing sessions filtered by workspace_path."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))

        workspace_a = temp_dir / "workspace_a"
        workspace_b = temp_dir / "workspace_b"
        workspace_a.mkdir()
        workspace_b.mkdir()

        session_a = hm.create_session(str(workspace_a), "model1")
        time.sleep(0.01)
        session_b = hm.create_session(str(workspace_b), "model2")

        # No filter: both sessions returned
        assert len(hm.list_sessions()) == 2

        # Filter to workspace_a: only session_a returned
        sessions = hm.list_sessions(workspace_path=str(workspace_a))
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == session_a

        # Filter to workspace_b: only session_b returned
        sessions = hm.list_sessions(workspace_path=str(workspace_b))
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == session_b

        # Filter to an unrelated workspace: nothing returned
        workspace_c = temp_dir / "workspace_c"
        workspace_c.mkdir()
        assert hm.list_sessions(workspace_path=str(workspace_c)) == []

    def test_delete_session(self, temp_dir):
        """Test deleting a session."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        session_id = hm.create_session("/test/workspace", "model")
        session_file = history_dir / f"session_{session_id}.json"
        
        assert session_file.exists()
        
        # Delete session
        result = hm.delete_session(session_id)
        
        assert result is True
        assert not session_file.exists()

    def test_delete_nonexistent_session(self, temp_dir):
        """Test deleting a session that doesn't exist."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        result = hm.delete_session("nonexistent_20250101_120000")
        assert result is False

    def test_export_session_json(self, temp_dir, sample_history_session):
        """Test exporting a session to JSON format."""
        history_dir = temp_dir / "history"
        history_dir.mkdir(parents=True)
        hm = HistoryManager(history_dir=str(history_dir))
        
        session_id = sample_history_session["session_id"]
        session_file = history_dir / f"session_{session_id}.json"
        session_file.write_text(json.dumps(sample_history_session))
        
        # Export to JSON
        output_path = temp_dir / "export.json"
        result = hm.export_session(session_id, str(output_path), format="json")
        
        assert result is True
        assert output_path.exists()
        
        # Verify exported content
        exported = json.loads(output_path.read_text())
        assert exported["session_id"] == session_id
        assert len(exported["messages"]) == 4

    def test_export_session_txt(self, temp_dir, sample_history_session):
        """Test exporting a session to TXT format."""
        history_dir = temp_dir / "history"
        history_dir.mkdir(parents=True)
        hm = HistoryManager(history_dir=str(history_dir))
        
        session_id = sample_history_session["session_id"]
        session_file = history_dir / f"session_{session_id}.json"
        session_file.write_text(json.dumps(sample_history_session))
        
        # Export to TXT
        output_path = temp_dir / "export.txt"
        result = hm.export_session(session_id, str(output_path), format="txt")
        
        assert result is True
        assert output_path.exists()
        
        # Verify content contains key information
        content = output_path.read_text()
        assert session_id in content
        assert "Hello, can you help me?" in content
        assert "factorial" in content

    def test_export_session_markdown(self, temp_dir, sample_history_session):
        """Test exporting a session to Markdown format."""
        history_dir = temp_dir / "history"
        history_dir.mkdir(parents=True)
        hm = HistoryManager(history_dir=str(history_dir))
        
        session_id = sample_history_session["session_id"]
        session_file = history_dir / f"session_{session_id}.json"
        session_file.write_text(json.dumps(sample_history_session))
        
        # Export to Markdown
        output_path = temp_dir / "export.md"
        result = hm.export_session(session_id, str(output_path), format="md")
        
        assert result is True
        assert output_path.exists()
        
        # Verify markdown structure
        content = output_path.read_text()
        assert "# Conversation Session" in content
        assert "### User" in content
        assert "### Assistant" in content
        assert "factorial" in content

    def test_export_nonexistent_session(self, temp_dir):
        """Test exporting a session that doesn't exist."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        output_path = temp_dir / "export.json"
        result = hm.export_session("nonexistent_20250101_120000", str(output_path))
        
        assert result is False
        assert not output_path.exists()

    def test_search_sessions(self, temp_dir):
        """Test searching sessions by content."""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        # Create sessions with different content
        session1 = hm.create_session("/workspace1", "model")
        hm.add_message(session1, "user", "How to implement factorial in Python?")
        hm.add_message(session1, "assistant", "Here's a factorial function...")
        
        time.sleep(0.01)  # Ensure file is written
        
        session2 = hm.create_session("/workspace2", "model")
        hm.add_message(session2, "user", "How to sort a list?")
        hm.add_message(session2, "assistant", "You can use the sorted() function...")
        
        # Search for factorial
        results = hm.search_sessions("factorial")
        assert len(results) == 1
        assert results[0]["session_id"] == session1
        
        # Search for sort
        results = hm.search_sessions("sort")
        assert len(results) == 1
        assert results[0]["session_id"] == session2

    def test_prune_old_sessions(self, temp_dir):
        """Test pruning old sessions"""
        history_dir = temp_dir / "history"
        hm = HistoryManager(history_dir=str(history_dir))
        
        # Create multiple sessions with delays to ensure distinct timestamps
        for i in range(5):
            hm.create_session(
                workspace_path=f"/workspace{i}",
                model="llama2"
            )
            time.sleep(0.01)  # Ensure distinct modification times
        
        # Verify we have 5 sessions
        sessions_before = hm.list_sessions()
        assert len(sessions_before) == 5
        
        # Prune to keep only 2
        pruned = hm.prune_old_sessions(keep_count=2)
        
        # Verify 3 were pruned
        assert pruned == 3
        
        # Verify only 2 remain
        sessions_after = hm.list_sessions()
        assert len(sessions_after) == 2
