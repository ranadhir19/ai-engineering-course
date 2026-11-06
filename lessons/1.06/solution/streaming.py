"""Streaming answers for the Inbox Assistant, on the raw wire.

Lesson AIE 1.04 -- APIs, SDKs & Streaming.

``StreamingProviderClient`` is the 1.03 budgeted client with one new
method, ``stream_chat``. The budgeter still stands in front (1.03's
rule: count before you send -- a stream you cannot afford is refused
locally, before a socket opens). What is new is the delivery: the
same completion the blocking ``chat`` returns whole, here arriving
as server-sent events, one word at a time.

A stream can end four ways, and only one of them is an error:

- ``completed``       -- the server sent its final chunk and [DONE].
- ``stop_sequence``   -- the caller's stop text appeared; the client
                         kept everything before it and hung up.
- ``cancelled``       -- the caller's cancel event fired mid-stream
                         (or was already set: then no request is
                         made at all, and the cancellation is free).
- ``dropped``         -- the connection closed without [DONE]. The
                         partial answer is NOT presented as whole:
                         ``completed`` is False and the text kept so
                         far rides home in the result, flagged.

In every case the caller gets a ``StreamResult`` -- never a bare
exception for a mid-stream event, never a silent truncation. (Errors
*before* the stream starts -- an over-large prompt, an unreachable
provider -- raise exactly the errors 1.02/1.03 already defined.)

Two honest limits, stated now because Act 3 measures both: the
client learns its usage from the server's final chunk, so a stream
that ends early carries ``usage = None`` -- what an aborted stream
actually cost is what the server *generated*, and from this side of
the wire that number is only knowable to within a chunk or two.
And hanging up is not instant from the server's side: it finds out
at its next write, up to one stream interval after you close.

Standard library only.
"""

import http.client
import json
import time
import urllib.parse

from budget import BudgetedProviderClient, BudgetExceededError
from inbox_client import (
    BadRequestError,
    ContextTooLargeError,
    ModelError,
    ProviderUnavailableError,
    cost_usd,
)
from tokenizer import count_messages_tokens


class StreamResult:
    """The outcome of one streamed call, however it ended.

    ``deltas`` are the content pieces as they arrived (each after
    the first begins with a space, exactly as the server sent
    them); ``text`` is their concatenation, cut at the stop
    sequence when one fired. ``chunk_offsets_s[i]`` is when delta
    i arrived, seconds after the request was sent; ``ttft_s`` is
    the first of those -- the number a blocking call cannot show
    you at all.
    """

    def __init__(self, provider, model):
        self.provider = provider
        self.model = model
        self.text = ""
        self.deltas = []
        self.chunk_offsets_s = []
        self.ttft_s = None
        self.elapsed_s = None
        self.completed = False
        self.stop_reason = None  # completed | stop_sequence | cancelled | dropped
        self.usage = None

    @property
    def chunks(self):
        return len(self.deltas)

    @property
    def partial(self):
        """True when ``text`` is not the whole answer."""
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
    """BudgetedProviderClient + ``stream_chat``.

    The budget check is identical to ``chat``'s: counted prompt
    tokens plus the reserve must fit the window, or
    ``BudgetExceededError`` is raised before any request exists.
    """

    def _check_budget(self, messages):
        prompt_tokens = count_messages_tokens(messages)
        if prompt_tokens + self.reserve_tokens > self.window:
            raise BudgetExceededError(
                self.provider_name, prompt_tokens, self.reserve_tokens, self.window
            )

    def stream_chat(self, messages, temperature=0.2, stop=None, cancel_event=None,
                    on_delta=None, chaos=None):
        """Stream one completion; return a StreamResult.

        ``stop`` -- a string: when it appears in the accumulated
        text, keep everything before it, hang up, and end with
        stop_reason "stop_sequence". ``cancel_event`` -- a
        threading.Event (or anything with ``is_set()``): checked
        before the request is sent and as chunks arrive; when set,
        hang up and end with stop_reason "cancelled".
        ``on_delta(piece, result)`` runs after each content chunk;
        it may set the cancel event. ``chaos`` is passed through to
        the stand-in servers' test hook (drop_after_chunks) -- real
        providers do not offer it; broken connections do.
        """
        result = StreamResult(self.provider_name, self.model)
        if cancel_event is not None and cancel_event.is_set():
            result.stop_reason = "cancelled"
            result.elapsed_s = 0.0
            return result
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
        if parts.scheme == "https":
            conn = http.client.HTTPSConnection(
                parts.hostname, parts.port or 443, timeout=self.timeout_s
            )
        else:
            conn = http.client.HTTPConnection(
                parts.hostname, parts.port or 80, timeout=self.timeout_s
            )
        start = time.perf_counter()
        response = None
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
            self._read_stream(response, result, start, stop, cancel_event, on_delta)
        finally:
            result.elapsed_s = time.perf_counter() - start
            self.last_elapsed_s = result.elapsed_s
            if result.usage is not None:
                self.last_usage = result.usage
                self.last_cost_usd = cost_usd(result.usage, self.provider_name)
            # Close the RESPONSE, not just the connection: the
            # response body holds the socket's file open, so a
            # connection closed on its own is a hang-up that never
            # reaches the wire. (Act 3 catches an SDK learning
            # this the expensive way.)
            if response is not None:
                response.close()
            conn.close()
        return result

    def _read_stream(self, response, result, start, stop, cancel_event, on_delta):
        text = ""
        while True:
            if cancel_event is not None and cancel_event.is_set():
                result.stop_reason = "cancelled"
                break
            line = response.readline()
            if not line:
                # The connection closed. Whether that is a clean end
                # or a drop is decided by what did NOT arrive: the
                # [DONE] that only a finished stream sends.
                if result.stop_reason is None:
                    result.stop_reason = "dropped"
                break
            line = line.strip()
            if not line.startswith(b"data:"):
                continue
            data = line[len(b"data:"):].strip()
            if data == b"[DONE]":
                result.completed = True
                result.stop_reason = "completed"
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
            if cancel_event is not None and cancel_event.is_set():
                result.stop_reason = "cancelled"
                break
            if stop and stop in text:
                result.text = text[: text.index(stop)].rstrip()
                result.stop_reason = "stop_sequence"
                break
        return result
