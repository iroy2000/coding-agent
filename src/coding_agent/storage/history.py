"""Conversation history management."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

console = Console()


class HistoryManager:
    """Manages conversation history storage and retrieval."""

    def __init__(self, history_dir: Optional[Path] = None) -> None:
        """
        Initialize history manager.

        Args:
            history_dir: Directory to store history files (defaults to ~/.coding-agent/history)
        """
        if history_dir is None:
            history_dir = Path.home() / ".coding-agent" / "history"
        
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_id: Optional[str] = None

    def _generate_session_id(self) -> str:
        """
        Generate a unique session ID based on timestamp.

        Returns:
            Session ID string
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def _get_session_file(self, session_id: str) -> Path:
        """
        Get the file path for a session.

        Args:
            session_id: Session identifier

        Returns:
            Path to session file
        """
        return self.history_dir / f"session_{session_id}.json"

    def create_session(self, workspace_path: str, model: str) -> str:
        """
        Create a new conversation session.

        Args:
            workspace_path: Current workspace path
            model: Model being used

        Returns:
            Session ID
        """
        session_id = self._generate_session_id()
        self.current_session_id = session_id

        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "workspace_path": workspace_path,
            "model": model,
            "messages": [],
        }

        self._save_session(session_id, session_data)
        return session_id

    def _save_session(self, session_id: str, data: Dict) -> None:
        """
        Save session data to file.

        Args:
            session_id: Session identifier
            data: Session data dictionary
        """
        session_file = self._get_session_file(session_id)
        
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save session: {e}[/yellow]")

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add a message to the session history.

        Args:
            session_id: Session identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata (e.g., file operations performed)
        """
        session_data = self.load_session(session_id)
        if not session_data:
            return

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }

        if metadata:
            message["metadata"] = metadata

        session_data["messages"].append(message)
        session_data["updated_at"] = datetime.now().isoformat()

        self._save_session(session_id, session_data)

    def load_session(self, session_id: str) -> Optional[Dict]:
        """
        Load a session from storage.

        Args:
            session_id: Session identifier

        Returns:
            Session data dictionary or None if not found
        """
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[red]Error loading session: {e}[/red]")
            return None

    def list_sessions(self, limit: Optional[int] = None) -> List[Dict]:
        """
        List all available sessions.

        Args:
            limit: Maximum number of sessions to return (None for all)

        Returns:
            List of session metadata dictionaries
        """
        sessions = []

        try:
            # Get all session files
            session_files = sorted(
                self.history_dir.glob("session_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True  # Most recent first
            )

            # Apply limit if specified
            if limit:
                session_files = session_files[:limit]

            for session_file in session_files:
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
                    # Extract metadata
                    metadata = {
                        "session_id": data.get("session_id"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at", data.get("created_at")),
                        "workspace_path": data.get("workspace_path"),
                        "model": data.get("model"),
                        "message_count": len(data.get("messages", [])),
                    }
                    sessions.append(metadata)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not read {session_file.name}: {e}[/yellow]")
                    continue

        except Exception as e:
            console.print(f"[red]Error listing sessions: {e}[/red]")

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if successful, False otherwise
        """
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            return False

        try:
            session_file.unlink()
            return True
        except Exception as e:
            console.print(f"[red]Error deleting session: {e}[/red]")
            return False

    def export_session(self, session_id: str, output_path: str, format: str = "json") -> bool:
        """
        Export a session to a file.

        Args:
            session_id: Session identifier
            output_path: Path to save exported file
            format: Export format (json, txt, md)

        Returns:
            True if successful, False otherwise
        """
        session_data = self.load_session(session_id)
        if not session_data:
            return False

        try:
            output_file = Path(output_path)

            if format == "json":
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)

            elif format == "txt":
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"Session: {session_data['session_id']}\n")
                    f.write(f"Created: {session_data['created_at']}\n")
                    f.write(f"Workspace: {session_data['workspace_path']}\n")
                    f.write(f"Model: {session_data['model']}\n")
                    f.write("\n" + "=" * 70 + "\n\n")

                    for msg in session_data.get("messages", []):
                        role = msg.get("role", "unknown").upper()
                        content = msg.get("content", "")
                        timestamp = msg.get("timestamp", "")
                        
                        f.write(f"[{timestamp}] {role}:\n")
                        f.write(f"{content}\n")
                        f.write("\n" + "-" * 70 + "\n\n")

            elif format == "md":
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"# Conversation Session: {session_data['session_id']}\n\n")
                    f.write(f"**Created:** {session_data['created_at']}  \n")
                    f.write(f"**Workspace:** `{session_data['workspace_path']}`  \n")
                    f.write(f"**Model:** {session_data['model']}  \n\n")
                    f.write("---\n\n")

                    for msg in session_data.get("messages", []):
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        timestamp = msg.get("timestamp", "")
                        
                        if role == "user":
                            f.write(f"### User\n")
                        elif role == "assistant":
                            f.write(f"### Assistant\n")
                        else:
                            f.write(f"### {role.title()}\n")
                        
                        f.write(f"*{timestamp}*\n\n")
                        f.write(f"{content}\n\n")
                        f.write("---\n\n")

            return True

        except Exception as e:
            console.print(f"[red]Error exporting session: {e}[/red]")
            return False

    def prune_old_sessions(self, keep_count: int = 50) -> int:
        """
        Delete old sessions, keeping only the most recent ones.

        Args:
            keep_count: Number of recent sessions to keep

        Returns:
            Number of sessions deleted
        """
        sessions = self.list_sessions()

        if len(sessions) <= keep_count:
            return 0

        # Delete older sessions
        deleted_count = 0
        for session in sessions[keep_count:]:
            session_id = session["session_id"]
            if self.delete_session(session_id):
                deleted_count += 1

        return deleted_count

    def search_sessions(self, query: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Search sessions by content.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching session metadata
        """
        matching_sessions = []
        query_lower = query.lower()

        try:
            session_files = sorted(
                self.history_dir.glob("session_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            for session_file in session_files:
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Search in messages
                    for msg in data.get("messages", []):
                        if query_lower in msg.get("content", "").lower():
                            metadata = {
                                "session_id": data.get("session_id"),
                                "created_at": data.get("created_at"),
                                "workspace_path": data.get("workspace_path"),
                                "model": data.get("model"),
                                "message_count": len(data.get("messages", [])),
                                "match": msg.get("content", "")[:200],  # Preview
                            }
                            matching_sessions.append(metadata)
                            break  # Only add each session once

                    if limit and len(matching_sessions) >= limit:
                        break

                except Exception:
                    continue

        except Exception as e:
            console.print(f"[red]Error searching sessions: {e}[/red]")

        return matching_sessions
