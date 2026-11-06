"""A deterministic, offline mock of a model *provider* endpoint.

Lesson AIE 1.04 -- APIs, SDKs & Streaming. (The 1.02/1.03 server,
plus the one new trick this lesson is about.)
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
- Generation is modelled honestly, and identically for both delivery
  modes: a completion of N words takes the profile's latency (the
  wait for the first token) plus (N - 1) x the profile's per-word
  stream interval to generate. A blocking call sleeps that whole
  time and then sends the finished text; a streaming call sleeps
  the latency, then sends one word per interval. Streaming changes
  when you may SEE the answer, never how long it takes to make --
  which is exactly the trade this lesson measures.
- POST with "stream": true answers as server-sent events: a role
  chunk, one content chunk per word, a final chunk carrying
  finish_reason and the usage object, then data: [DONE]. The
  streamed words concatenate to exactly the blocking answer.
- A request may carry "chaos": {"drop_after_chunks": N} -- a test
  hook: the server closes the connection abruptly after N content
  chunks, with no final chunk and no [DONE]. Real streams break
  mid-flight; the lesson needs one that does it on demand.
- GET /__count returns {"requests": n} for harnesses.
- GET /__stream_stats returns one record per streamed request:
  how many content chunks were actually written, how many the full
  answer had, and how the stream ended from the server's side
  ("completed", "dropped_by_server", or "client_disconnected" --
  the last is how an abort looks from over there).
"""

import argparse
import json
import re
import socket
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
        "stream_interval_s": 0.025,
        "price_in_per_mtok": 0.15,
        "price_out_per_mtok": 0.30,
    },
    "atlas": {
        "model": "atlas-1",
        "port": 8772,
        "context_tokens": 4000,
        "latency_s": 0.15,
        "stream_interval_s": 0.015,
        "price_in_per_mtok": 0.80,
        "price_out_per_mtok": 1.60,
    },
    "oracle": {
        "model": "oracle-1",
        "port": 8773,
        "context_tokens": 20000,
        "latency_s": 0.60,
        "stream_interval_s": 0.040,
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


def generation_s(profile, content):
    """Wall-clock seconds this completion takes to generate."""
    words = max(1, count_tokens(content))
    return profile["latency_s"] + (words - 1) * profile["stream_interval_s"]


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
        self.streams = []
        self.lock = threading.Lock()

    def next_request_number(self):
        with self.lock:
            self.requests += 1
            return self.requests

    def record_stream(self, record):
        with self.lock:
            self.streams.append(record)


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
            elif self.path == "/__stream_stats":
                with state.lock:
                    streams = list(state.streams)
                self._send_json(200, {"streams": streams})
            else:
                self._send_json(404, error_body("not found", "not_found"))

        def _answer_for(self, data):
            """Validate the request; return (content, prompt_text) or
            send an error and return None."""
            messages = data.get("messages")
            if not messages:
                self._send_json(
                    400,
                    error_body("invalid JSON or missing messages", "invalid_request_error"),
                )
                return None
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
                return None
            last_user = ""
            for message in reversed(messages):
                if isinstance(message, dict) and message.get("role") == "user":
                    last_user = str(message.get("content", ""))
                    break
            first_word = last_user.strip().split(None, 1)[0].lower() if last_user.strip() else ""
            if first_word in ("summarise", "summarize"):
                return digest_answer(), prompt_text
            return extractive_answer(last_user), prompt_text

        def _stream(self, number, data, content, prompt_text):
            words = content.split(" ")
            usage = {
                "prompt_tokens": count_tokens(prompt_text),
                "completion_tokens": len(words),
                "total_tokens": count_tokens(prompt_text) + len(words),
            }
            chaos = data.get("chaos") or {}
            drop_after = chaos.get("drop_after_chunks")
            record = {
                "request": number,
                "model": profile["model"],
                "chunks_sent": 0,
                "total_chunks": len(words),
                "outcome": "completed",
            }
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

            def event(obj):
                self.wfile.write(("data: " + json.dumps(obj) + "\n\n").encode("utf-8"))
                self.wfile.flush()

            base = {"id": "chatcmpl-mock-" + str(number),
                    "object": "chat.completion.chunk", "model": profile["model"]}
            try:
                # Time to first token: the profile's latency, as a
                # blocking caller would also pay it -- inside the wait.
                time.sleep(profile["latency_s"])
                event(dict(base, choices=[{"index": 0,
                                           "delta": {"role": "assistant", "content": ""},
                                           "finish_reason": None}]))
                for i, word in enumerate(words):
                    piece = word if i == 0 else " " + word
                    event(dict(base, choices=[{"index": 0,
                                               "delta": {"content": piece},
                                               "finish_reason": None}]))
                    record["chunks_sent"] = i + 1
                    if drop_after is not None and record["chunks_sent"] >= drop_after:
                        record["outcome"] = "dropped_by_server"
                        state.record_stream(record)
                        # The abrupt part: no final chunk, no [DONE],
                        # just a closed connection mid-sentence.
                        try:
                            self.connection.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                        self.connection.close()
                        return
                    if i < len(words) - 1:
                        time.sleep(profile["stream_interval_s"])
                event(dict(base,
                           choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}],
                           usage=usage))
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                # The client hung up. From the server's side this is
                # what every abort looks like -- and it is only
                # visible at the NEXT write, one interval later.
                record["outcome"] = "client_disconnected"
            state.record_stream(record)

        def do_POST(self):
            if self.path != COMPLETIONS_PATH:
                self._send_json(404, error_body("not found", "not_found"))
                return
            number = state.next_request_number()
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                data = json.loads(raw.decode("utf-8")) if raw else None
            except (ValueError, UnicodeDecodeError):
                data = None
            if not isinstance(data, dict):
                self._send_json(
                    400,
                    error_body("invalid JSON or missing messages", "invalid_request_error"),
                )
                return
            answered = self._answer_for(data)
            if answered is None:
                return
            content, prompt_text = answered
            if data.get("stream"):
                self._stream(number, data, content, prompt_text)
                return
            # Blocking delivery: the same generation, waited out in
            # full before a single byte comes back.
            time.sleep(generation_s(profile, content))
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
