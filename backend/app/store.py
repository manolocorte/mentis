"""Conversation store. Local JSON for now; swappable for DynamoDB on-demand at deploy
(same interface). Single occasional user → trivial volume.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from .config import get_settings


class LocalStore:
    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def _write(self, data: dict) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._path)

    def new_conversation(self) -> str:
        return uuid.uuid4().hex

    def append(self, conversation_id: str, role: str, content: str) -> None:
        data = self._read()
        conv = data.setdefault(conversation_id, [])
        conv.append({"role": role, "content": content, "ts": time.time()})
        self._write(data)

    def history(self, conversation_id: str, limit: int = 20) -> list[dict]:
        return self._read().get(conversation_id, [])[-limit:]


def get_store():
    s = get_settings()
    # DynamoDB adapter to be added for deploy; same method surface.
    return LocalStore(s.store_path)
