#!/usr/bin/env python3
"""Static quiz app server with a tiny SQLite sync API."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("QINGBEI_DB", DATA_DIR / "sync.sqlite3"))
USER_RE = re.compile(r"^[A-Za-z0-9_-]{3,40}$")
MAX_BODY = 2 * 1024 * 1024


def db() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_state (
            user_key TEXT PRIMARY KEY,
            state_json TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """
    )
    return conn


def valid_user(value: str) -> bool:
    return bool(USER_RE.fullmatch(value or ""))


def merge_unique(*lists: object) -> list:
    merged: list = []
    for value in lists:
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str) and item not in merged:
                merged.append(item)
    return merged


def merge_mistakes(base: object, incoming: object) -> dict:
    result: dict = {}
    for source in (base, incoming):
        if not isinstance(source, dict):
            continue
        for question_id, item in source.items():
            if not isinstance(question_id, str):
                continue
            count = 0
            if isinstance(item, dict):
                try:
                    count = max(0, min(2, int(item.get("correctCount", 0))))
                except Exception:
                    count = 0
            current = result.get(question_id, {"correctCount": 0})
            result[question_id] = {"correctCount": max(current.get("correctCount", 0), count)}
    return result


def merge_dict(base: object, incoming: object) -> dict:
    result = dict(base) if isinstance(base, dict) else {}
    if isinstance(incoming, dict):
        result.update(incoming)
    return result


def merge_state(base: object, incoming: object) -> dict:
    if not isinstance(base, dict):
        base = {}
    if not isinstance(incoming, dict):
        incoming = {}
    merged = dict(base)
    merged.update(incoming)
    merged["favorites"] = merge_unique(base.get("favorites"), incoming.get("favorites"))
    merged["mistakes"] = merge_mistakes(base.get("mistakes"), incoming.get("mistakes"))
    for key in ("quizPositions", "quizOrders", "answers", "favoriteAnswers", "mistakeAnswers"):
        merged[key] = merge_dict(base.get(key), incoming.get(key))
    return merged


class Handler(SimpleHTTPRequestHandler):
    server_version = "QingbeiSync/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "no-cache")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        if self.path.startswith("/api/"):
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        super().do_OPTIONS()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.write_json({"ok": True})
            return
        if parsed.path == "/api/state":
            user = parse_qs(parsed.query).get("user", [""])[0].strip()
            if not valid_user(user):
                self.write_json({"ok": False, "error": "invalid_user"}, HTTPStatus.BAD_REQUEST)
                return
            with db() as conn:
                row = conn.execute("SELECT state_json, updated_at FROM user_state WHERE user_key = ?", (user,)).fetchone()
            if not row:
                self.write_json({"ok": True, "user": user, "state": None, "updatedAt": None})
                return
            self.write_json({"ok": True, "user": user, "state": json.loads(row[0]), "updatedAt": row[1]})
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/state":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > MAX_BODY:
            self.write_json({"ok": False, "error": "invalid_body_size"}, HTTPStatus.BAD_REQUEST)
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.write_json({"ok": False, "error": "invalid_json"}, HTTPStatus.BAD_REQUEST)
            return
        user = str(payload.get("user", "")).strip()
        state = payload.get("state")
        if not valid_user(user):
            self.write_json({"ok": False, "error": "invalid_user"}, HTTPStatus.BAD_REQUEST)
            return
        if not isinstance(state, dict):
            self.write_json({"ok": False, "error": "invalid_state"}, HTTPStatus.BAD_REQUEST)
            return
        updated_at = int(time.time() * 1000)
        with db() as conn:
            row = conn.execute("SELECT state_json FROM user_state WHERE user_key = ?", (user,)).fetchone()
            existing = json.loads(row[0]) if row else {}
            state_json = json.dumps(merge_state(existing, state), ensure_ascii=False, separators=(",", ":"))
            conn.execute(
                """
                INSERT INTO user_state(user_key, state_json, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(user_key) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (user, state_json, updated_at),
            )
        self.write_json({"ok": True, "user": user, "updatedAt": updated_at})

    def write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    db().close()
    print(f"Serving {ROOT} on http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()

