import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """In-memory session manager for the demo API."""

    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def _get_current_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_session(self, user_id: Optional[str] = None, session_name: Optional[str] = None,
                       session_id: Optional[str] = None) -> str:
        if not session_id:
            session_id = str(uuid.uuid4())

        self.active_sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id or "unknown",
            "session_name": session_name or f"session_{session_id[:8]}",
            "created_at": self._get_current_timestamp(),
            "last_activity": self._get_current_timestamp(),
            "query_count": 0,
        }
        logger.info(f"Created session: {session_id} for user: {user_id}")
        return session_id

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.active_sessions.get(session_id)

    def update_session_activity(self, session_id: str):
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = self._get_current_timestamp()
            self.active_sessions[session_id]["query_count"] += 1

    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if user_id:
            return [s for s in self.active_sessions.values() if s["user_id"] == user_id]
        return list(self.active_sessions.values())

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
