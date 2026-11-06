"""A deterministic, offline mock of a model *provider* endpoint.

Lesson AIE 1.02 -- Models & Providers.
Standard library only: http.server, json, argparse, re, time, threading.

One process emulates ONE provider. Start three processes with three
different --profile values and you have three providers that differ the
way real providers differ: model name, context limit, simulated latency,
and a published price table (US dollars per million tokens, input and
output priced separately -- the way the market prices tiers).

    python3 mock_provider_server.py --profile sprout    # port 8771
    python3 mock_provider_server.py --profile atlas     # port 8772
    python3 mock_provider_server.py --profile oracle    # port 8773

Behaviour:
- POST /v1/chat/completions, the same shape as Lesson 1.01's server.
- The prompt's token count (whitespace words, exactly as 1.01 counted)
  is checked against the profile's context limit. Over the limit: HTTP
  400 with error code "context_length_exceeded" -- a rejection, never a
  silent truncation.
- Answers are extractive, like 1.01: keyword overlap against the same
  built-in inbox. A user message starting with "summarise" (or
  "summarize") gets a digest of all three emails instead.
- Every request sleeps the profile's simulated latency first, so timing
  differences between providers are real wall-clock differences.
- GET /__count returns {"requests": n} for harnesses.
"""

import argparse
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

COMPLETIONS_PATH = "/v1/chat/completions"

PROFILES = {
    "sprout": {
        "model": "sprout-1",
        "port": 8771,
        "context_tokens": 600,
        "latency_s": 0.30,
        "price_in_per_mtok": 0.15,
        "price_out_per_mtok": 0.30,
    },
    "atlas": {
        "model": "atlas-1",
        "port": 8772,
        "context_tokens": 4000,
        "latency_s": 0.15,
        "price_in_per_mtok": 0.80,
        "price_out_per_mtok": 1.60,
    },
    "oracle": {
        "model": "oracle-1",
        "port": 8773,
        "context_tokens": 20000,
        "latency_s": 0.60,
        "price_in_per_mtok": 5.00,
        "price_out_per_mtok": 15.00,
    },
}

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


def digest_answer():
    """The stand-in's 'summary': one key sentence per email, labelled."""
    lines = []
    for email in EMAILS:
        lines.append(email["subject"] + ": " + email["sentences"][0])
    return " ".join(lines)


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


def error_body(message, kind, code=None):
    return {"error": {"message": message, "type": kind, "code": code}}


class State:
    def __init__(self, profile):
        self.profile = profile
        self.requests = 0
        self.lock = threading.Lock()

    def next_request_number(self):
        with self.lock:
            self.requests += 1
            return self.requests


def make_handler(state):
    profile = state.profile

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
            elif self.path == "/__profile":
                self._send_json(200, profile)
            else:
                self._send_json(404, error_body("not found", "not_found"))

        def do_POST(self):
            if self.path != COMPLETIONS_PATH:
                self._send_json(404, error_body("not found", "not_found"))
                return
            number = state.next_request_number()
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""

            # Simulated provider latency: real wall-clock time, so the
            # client's stopwatch measures something true.
            time.sleep(profile["latency_s"])

            try:
                data = json.loads(raw.decode("utf-8")) if raw else None
            except (ValueError, UnicodeDecodeError):
                data = None
            if not isinstance(data, dict) or not data.get("messages"):
                self._send_json(
                    400,
                    error_body("invalid JSON or missing messages", "invalid_request_error"),
                )
                return
            messages = data["messages"]
            prompt_text = " ".join(
                str(m.get("content", "")) for m in messages if isinstance(m, dict)
            )
            prompt_tokens = count_tokens(prompt_text)
            if prompt_tokens > profile["context_tokens"]:
                self._send_json(
                    400,
                    error_body(
                        "context_length_exceeded: prompt_tokens "
                        + str(prompt_tokens)
                        + " exceeds context limit "
                        + str(profile["context_tokens"])
                        + " for model "
                        + profile["model"],
                        "invalid_request_error",
                        code="context_length_exceeded",
                    ),
                )
                return
            last_user = ""
            for message in reversed(messages):
                if isinstance(message, dict) and message.get("role") == "user":
                    last_user = str(message.get("content", ""))
                    break
            first_word = last_user.strip().split(None, 1)[0].lower() if last_user.strip() else ""
            if first_word in ("summarise", "summarize"):
                content = digest_answer()
            else:
                content = extractive_answer(last_user)
            completion = chat_completion(profile["model"], content, prompt_text)
            completion["id"] = "chatcmpl-mock-" + str(number)
            self._send_json(200, completion)

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Mock provider server (stdlib only).")
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES))
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    profile = dict(PROFILES[args.profile])
    port = args.port if args.port is not None else profile["port"]
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(State(profile)))
    print(
        "mock_provider_server profile="
        + args.profile
        + " model="
        + profile["model"]
        + " listening on 127.0.0.1:"
        + str(port),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
