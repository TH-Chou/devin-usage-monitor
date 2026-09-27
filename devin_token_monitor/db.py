"""Read-only access to the Devin CLI sessions database.

Devin CLI stores every chat message as JSON in
``~/.local/share/devin/cli/sessions.db`` (SQLite, WAL mode).  Assistant
messages that performed model inference carry per-request metrics under
``chat_message.metadata.metrics`` (input/output/cache token counts) and
``chat_message.metadata.generation_model``.

``fetch_usage_rows`` returns one :class:`UsageRow` per inference request.
``row_id`` is a monotonic watermark, so callers can poll incrementally.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "devin" / "cli" / "sessions.db"
ENV_DB_PATH = "DEVIN_SESSIONS_DB"

_QUERY = """
SELECT
  mn.row_id,
  mn.session_id,
  s.title,
  s.working_directory,
  s.model AS session_model,
  json_extract(mn.chat_message, '$.metadata.generation_model'),
  json_extract(mn.chat_message, '$.metadata.request_id'),
  json_extract(mn.chat_message, '$.message_id'),
  json_extract(mn.chat_message, '$.metadata.metrics.input_tokens'),
  json_extract(mn.chat_message, '$.metadata.metrics.output_tokens'),
  json_extract(mn.chat_message, '$.metadata.metrics.cache_read_tokens'),
  json_extract(mn.chat_message, '$.metadata.metrics.cache_creation_tokens'),
  json_extract(mn.chat_message, '$.metadata.metrics.ttft_ms'),
  json_extract(mn.chat_message, '$.metadata.metrics.total_time_ms'),
  json_extract(mn.chat_message, '$.metadata.metrics.tokens_per_sec'),
  json_extract(mn.chat_message, '$.metadata.created_at'),
  mn.created_at
FROM message_nodes mn
JOIN sessions s ON s.id = mn.session_id
WHERE mn.row_id > ?
  AND json_extract(mn.chat_message, '$.metadata.metrics') IS NOT NULL
ORDER BY mn.row_id
"""


def db_path() -> Path:
    return Path(os.environ.get(ENV_DB_PATH, DEFAULT_DB_PATH)).expanduser()


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or db_path()
    if not path.exists():
        raise FileNotFoundError(f"Devin sessions database not found: {path}")
    uri = f"{path.resolve().as_uri()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _parse_ts(iso: object, fallback_unix: int) -> datetime:
    if isinstance(iso, str):
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.fromtimestamp(fallback_unix, tz=timezone.utc)


@dataclass
class UsageRow:
    row_id: int
    session_id: str
    session_title: str
    working_directory: str
    model: str  # model that actually served the request
    request_id: str
    message_id: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    ttft_ms: float | None
    total_time_ms: float | None
    tokens_per_sec: float | None
    ts: datetime  # request timestamp (UTC)


def fetch_message_body(
    conn: sqlite3.Connection, request_id: str, message_id: str
) -> str:
    """Return the plaintext content of one assistant message, looked up by
    request/message id. Replicated message-tree nodes share the same content,
    so the first hit wins."""
    for json_path, identifier in (
        ("$.metadata.request_id", request_id),
        ("$.message_id", message_id),
    ):
        if not identifier:
            continue
        for r in conn.execute(
            """SELECT json_extract(chat_message, '$.content')
               FROM message_nodes
               WHERE json_extract(chat_message, ?) = ?
               ORDER BY row_id""",
            (json_path, identifier),
        ):
            if isinstance(r[0], str) and r[0].strip():
                return r[0]
    return ""


def fetch_usage_rows(conn: sqlite3.Connection, after_row_id: int = 0) -> list[UsageRow]:
    rows: list[UsageRow] = []
    for r in conn.execute(_QUERY, (after_row_id,)):
        model = r[5] or r[4] or "unknown"
        rows.append(
            UsageRow(
                row_id=r[0],
                session_id=r[1],
                session_title=r[2] or "(untitled)",
                working_directory=r[3] or "",
                model=str(model),
                request_id=r[6] or "",
                message_id=r[7] or "",
                input_tokens=int(r[8] or 0),
                output_tokens=int(r[9] or 0),
                cache_read_tokens=int(r[10] or 0),
                cache_creation_tokens=int(r[11] or 0),
                ttft_ms=r[12],
                total_time_ms=r[13],
                tokens_per_sec=r[14],
                ts=_parse_ts(r[15], r[16]),
            )
        )
    return rows
