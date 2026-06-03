from collections import defaultdict
from datetime import datetime

_sessions: dict[str, list[dict]] = defaultdict(list)
_timestamps: dict[str, datetime] = {}

MAX_TURNS = 10  # keep last 10 exchanges (20 messages)


def get_history(session_id: str) -> list[dict]:
    return list(_sessions[session_id][-(MAX_TURNS * 2):])


def append(session_id: str, role: str, content: str) -> None:
    _sessions[session_id].append({"role": role, "content": content})
    _timestamps[session_id] = datetime.now()


def clear(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _timestamps.pop(session_id, None)
