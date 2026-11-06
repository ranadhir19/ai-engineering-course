"""Streaming answers (exercise starter).

The transport is given. This module already opens the stream,
parses the server-sent events, assembles the text, times the
chunks, and stands behind the 1.03 budget guard -- a happy-path
stream completes correctly through it, and an over-budget prompt
is refused before a socket opens.

What it does not do is end a stream any way except eventually:

- ``stop`` is accepted and ignored: the stream runs to the last
  word whatever your policy said.
- ``cancel_event`` is accepted and ignored: there is no way to
  stop reading a runaway answer short of killing the process.
- A connection that closes early is reported as ``completed`` --
  the reader cannot tell a finished stream from a cut one, so a
  partial answer is handed back dressed as a whole one. That is
  the worst of the three, and it is silent.

Your exercise (statement in README.md in this folder): give the
stream its termination discipline -- a stop condition, a
mid-stream cancellation that costs nothing when it lands early,
and a dropped stream that comes home partial and flagged, never
dressed as finished. The graded starting point is this file; the
harness is stream_harness.py; the worked answer is in solution/.
"""

import http.client
import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "solution"))

from budget import BudgetedProviderClient, BudgetExceededError  # noqa: E402
from inbox_client import (  # noqa: E402
    BadRequestError,
    ContextTooLargeError,
    ModelError,
    ProviderUnavailableError,
    cost_usd,
)
from tokenizer import count_messages_tokens  # noqa: E402


class StreamResult:
    """The outcome of one streamed call (same shape as the lesson's)."""

    def __init__(self, provider, model):
        self.provider = provider
        self.model = model
        self.text = ""
        self.deltas = []
        self.chunk_offsets_s = []
        self.ttft_s = None
        self.elapsed_s = None
        self.completed = False
        self.stop_reason = None
        self.usage = None

    @property
    def chunks(self):
        return len(self.deltas)

    @property
    def partial(self):
        return not self.completed

    def __repr__(self):
        return (
            "StreamResult(provider=%r, chunks=%d, completed=%r, stop_reason=%r, "
            "ttft_s=%s, elapsed_s=%s)"
            % (
                self.provider,
                self.chunks,
                self.completed,
                self.stop_reason,
                None if self.ttft_s is None else round(self.ttft_s, 3),
                None if self.elapsed_s is None else round(self.elapsed_s, 3),
            )
        )


class StreamingProviderClient(BudgetedProviderClient):
    """The happy-path streamer: correct while nothing goes wrong."""

    def _check_budget(self, messages):
        prompt_tokens = count_messages_tokens(messages)
        if prompt_tokens + self.reserve_tokens > self.window:
            raise BudgetExceededError(
                self.provider_name, prompt_tokens, self.reserve_tokens, self.window
            )

    def stream_chat(self, messages, temperature=0.2, stop=None, cancel_event=None,
                    on_delta=None, chaos=None):
        # NOTE (the exercise): ``stop`` and ``cancel_event`` are part
        # of the signature the harness grades, and this starter
        # accepts them without acting on either. Implementing them
        # -- plus honest drop handling below -- is the task.
        result = StreamResult(self.provider_name, self.model)
        self._check_budget(messages)
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if chaos:
            payload["chaos"] = chaos
        parts = urllib.parse.urlparse(self.base_url + "/v1/chat/completions")
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        conn = http.client.HTTPConnection(
            parts.hostname, parts.port or 80, timeout=self.timeout_s
        )
        start = time.perf_counter()
        try:
            try:
                conn.request("POST", parts.path, body=body, headers=headers)
                response = conn.getresponse()
            except (OSError, http.client.HTTPException) as exc:
                raise ProviderUnavailableError(
                    "provider " + self.provider_name + " (" + self.model + ") "
                    "unavailable: " + str(exc)
                ) from exc
            if response.status != 200:
                text = response.read().decode("utf-8", errors="replace")
                if response.status == 400 and "context_length_exceeded" in text:
                    raise ContextTooLargeError(
                        "provider " + self.provider_name + " (" + self.model + ") "
                        "rejected the prompt: " + text[:200]
                    )
                if response.status == 400:
                    raise BadRequestError("400 bad request: " + text[:200])
                raise ModelError(
                    "unexpected HTTP status " + str(response.status) + ": " + text[:200]
                )
            text = ""
            while True:
                line = response.readline()
                if not line:
                    break
                line = line.strip()
                if not line.startswith(b"data:"):
                    continue
                data = line[len(b"data:"):].strip()
                if data == b"[DONE]":
                    break
                try:
                    chunk = json.loads(data.decode("utf-8"))
                except ValueError:
                    continue
                if isinstance(chunk.get("usage"), dict):
                    result.usage = chunk["usage"]
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                piece = (choices[0].get("delta") or {}).get("content") or ""
                if not piece:
                    continue
                now = time.perf_counter() - start
                if result.ttft_s is None:
                    result.ttft_s = now
                result.deltas.append(piece)
                result.chunk_offsets_s.append(now)
                text += piece
                result.text = text
                if on_delta is not None:
                    on_delta(piece, result)
            # STARTER FLAW, deliberate: every way of reaching this
            # line -- [DONE], a clean EOF, a cut connection -- is
            # reported the same way. The harness scenario
            # drop_keeps_partial exists because of this block.
            result.completed = True
            result.stop_reason = "completed"
        finally:
            result.elapsed_s = time.perf_counter() - start
            self.last_elapsed_s = result.elapsed_s
            if result.usage is not None:
                self.last_usage = result.usage
                self.last_cost_usd = cost_usd(result.usage, self.provider_name)
            conn.close()
        return result
