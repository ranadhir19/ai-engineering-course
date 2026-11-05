"""A deterministic, offline mock of a chat-completions model endpoint.

Lesson AIE 1.01 -- The Toolkit: Python, JSON & HTTP.
Standard library only: http.server, json, argparse, re, time, threading.

Usage:
    python3 mock_model_server.py --port 8765 --mode ok

Modes:
    ok            Answer extractively from the built-in inbox (default).
    auth          401 unless an "Authorization: Bearer ..." header is present.
    ratelimit2    First 2 requests get 429 + "Retry-After: 1", then ok.
    server_error  Always 500 with a JSON error body.
    bad_request   Always 400 with a JSON error body.
    malformed     200 with a body that is not JSON at all.
    slow          Sleeps 30 seconds, then answers like ok.

Also: GET /__count returns {"requests": n}, the number of POSTs received
on the completions path, so test harnesses can assert attempt counts.
"""

import argparse
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

COMPLETIONS_PATH = "/v1/chat/completions"

EMAILS = [
    {
        "subject": "Project Aurora launch date",
        "sentences": [
            "Project Aurora will launch on Wednesday, November 18, 2026.",
            "The launch rehearsal is on November 14, 2026, and the support rota starts on launch morning.",
            "Please hold questions about the launch date until the rehearsal notes are out.",
        ],
    },
    {
        "subject": "Budget approval for the inbox assistant",
        "sentences": [
            "Finance has approved the budget of 48000 dollars for the inbox assistant project.",
            "The approved budget covers hosting and evaluation, and spending can start immediately.",
            "Please send budget receipts to Finance by Friday.",
        ],
    },
    {
        "subject": "Design review meeting rescheduled",
        "sentences": [
            "The design review meeting has been rescheduled to Thursday at 2 pm in Room 4B.",
            "The meeting was originally planned for Wednesday morning.",
            "Please update your calendar for the rescheduled meeting time.",
        ],
    },
]

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "when", "what", "who",
    "has", "have", "had", "been", "be", "it", "its", "of", "on", "in",
    "to", "for", "and", "or", "about", "please", "tell", "me", "do",
    "does", "did", "will", "would", "can", "could", "i", "you", "we",
}

NO_MATCH = (
    "I searched the inbox and found nothing on that topic. "
    "The inbox covers a project launch, a budget approval, and a meeting reschedule."
)


def keywords(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def extractive_answer(question):
    """Score each email by keyword overlap; return its best sentence(s)."""
    wanted = keywords(question)
    best_email = None
    best_score = 0
    for email in EMAILS:
        haystack = keywords(email["subject"] + " " + " ".join(email["sentences"]))
        score = len(wanted & haystack)
        if score > best_score:
            best_score = score
            best_email = email
    if best_email is None or best_score == 0:
        return NO_MATCH
    hits = [s for s in best_email["sentences"] if keywords(s) & wanted]
    if not hits:
        hits = best_email["sentences"][:1]
    return " ".join(hits)


def count_tokens(text):
    return len(text.split())


def chat_completion(model, content, prompt_text):
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": count_tokens(prompt_text),
            "completion_tokens": count_tokens(content),
            "total_tokens": count_tokens(prompt_text) + count_tokens(content),
        },
    }


def error_body(message, kind):
    return {"error": {"message": message, "type": kind, "code": None}}


class State:
    def __init__(self, mode):
        self.mode = mode
        self.requests = 0
        self.lock = threading.Lock()

    def next_request_number(self):
        with self.lock:
            self.requests += 1
            return self.requests


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):  # keep the console quiet
            pass

        def _send(self, status, body_bytes, content_type="application/json", extra=None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body_bytes)))
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body_bytes)

        def _send_json(self, status, obj, extra=None):
            self._send(status, json.dumps(obj).encode("utf-8"), extra=extra)

        def do_GET(self):
            if self.path == "/__count":
                with state.lock:
                    n = state.requests
                self._send_json(200, {"requests": n})
            else:
                self._send_json(404, error_body("not found", "not_found"))

        def do_POST(self):
            if self.path != COMPLETIONS_PATH:
                self._send_json(404, error_body("not found", "not_found"))
                return
            number = state.next_request_number()
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""

            if state.mode == "auth" and not (self.headers.get("Authorization") or "").startswith("Bearer "):
                self._send_json(401, error_body("missing or invalid API key", "auth_error"))
                return
            if state.mode == "ratelimit2" and number <= 2:
                self._send_json(
                    429,
                    error_body("rate limit exceeded, slow down", "rate_limit_error"),
                    extra={"Retry-After": "1"},
                )
                return
            if state.mode == "server_error":
                self._send_json(500, error_body("internal server error", "server_error"))
                return
            if state.mode == "bad_request":
                self._send_json(400, error_body("bad request", "invalid_request_error"))
                return
            if state.mode == "malformed":
                self._send(200, b"this is not json {", content_type="text/plain")
                return
            if state.mode == "slow":
                time.sleep(30)

            # ok behaviour (also the tail of auth / ratelimit2 / slow)
            try:
                data = json.loads(raw.decode("utf-8")) if raw else None
            except (ValueError, UnicodeDecodeError):
                data = None
            if not isinstance(data, dict) or not data.get("messages"):
                self._send_json(400, error_body("invalid JSON or missing messages", "invalid_request_error"))
                return
            messages = data["messages"]
            last_user = ""
            for message in reversed(messages):
                if isinstance(message, dict) and message.get("role") == "user":
                    last_user = str(message.get("content", ""))
                    break
            prompt_text = " ".join(
                str(m.get("content", "")) for m in messages if isinstance(m, dict)
            )
            content = extractive_answer(last_user)
            model = data.get("model") or "inbox-1"
            completion = chat_completion(model, content, prompt_text)
            completion["id"] = "chatcmpl-mock-" + str(number)
            self._send_json(200, completion)

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Mock chat-completions server (stdlib only).")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--mode",
        default="ok",
        choices=["ok", "auth", "ratelimit2", "server_error", "bad_request", "malformed", "slow"],
    )
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(State(args.mode)))
    print("mock_model_server listening on 127.0.0.1:" + str(args.port) + " mode=" + args.mode, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
