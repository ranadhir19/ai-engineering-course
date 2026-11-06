"""A small provider SDK, of the kind that wants to replace your client.

Lesson AIE 1.04 -- APIs, SDKs & Streaming.

This is a miniature of the real thing, written for the course so
that its behaviour can be measured rather than argued about. It is
not a caricature: it does what real SDKs do. It builds the JSON,
carries the key, parses the responses, and hands you friendly
objects -- ``create`` for a whole answer, ``create_stream`` for an
iterator of text deltas. For the happy path it is genuinely nicer
than the raw wire. That is why people adopt SDKs, and the lesson
says so.

What it does not hand you is the wire's evidence:

- No clock. A blocking ``create`` reports the total elapsed time,
  but nothing in either call will tell you when the first token
  arrived. Time-to-first-token -- the number that decides whether
  a streamed UI feels alive -- is not in the object model.
- No partials. ``create_stream`` yields strings and keeps nothing
  public. If the connection drops mid-stream, iteration raises
  ``SDKStreamError`` and the text that already arrived exists
  nowhere on the object: not on the stream, not on the error. If
  you wanted it, you had to be keeping it yourself -- at which
  point you are maintaining the raw client's result object by hand,
  inside the SDK's abstraction.
- No reflexive abort. A stream closes when you call ``close()``
  (or when the object is collected). The natural thing -- breaking
  out of the loop -- calls nothing: while the stream object lives,
  the connection stays open and the server keeps generating, and
  billing, tokens nobody will read. Act 3 measures all three
  patterns against the stand-ins' stream statistics.

None of this makes the SDK bad. It makes it a trade: convenience
now, visibility later -- and the visibility is exactly what you
reach for on the day the stream breaks. Standard library only.
"""

import http.client
import json
import time
import urllib.parse

from inbox_client import PROVIDERS


class SDKError(Exception):
    """Every failure this SDK reports, flattened to one type."""


class SDKStreamError(SDKError):
    """A stream failed mid-iteration. Carries no partial output."""


class SDKResponse:
    """A completed blocking call: text, usage, and the total time.

    Note what is not here: when the answer's first token arrived.
    With a blocking call the SDK cannot know -- and with a streamed
    call, below, it does not say.
    """

    def __init__(self, text, usage, elapsed_s):
        self.text = text
        self.usage = usage
        self.elapsed_s = elapsed_s


class SDKStream:
    """An iterator of text deltas over one open connection.

    The deltas it has yielded are gone from the object's point of
    view the moment they are yielded. ``close()`` hangs up the
    connection deliberately; abandoning the iterator does not --
    cleanup waits for the object's collection, whenever that is.
    """

    def __init__(self, conn, response):
        self._conn = conn
        self._response = response
        self._done = False

    def __iter__(self):
        return self

    def __next__(self):
        if self._done:
            raise StopIteration
        while True:
            line = self._response.readline()
            if not line:
                self._done = True
                self.close()
                raise SDKStreamError(
                    "stream closed by the server before it finished"
                )
            line = line.strip()
            if not line.startswith(b"data:"):
                continue
            data = line[len(b"data:"):].strip()
            if data == b"[DONE]":
                self._done = True
                self.close()
                raise StopIteration
            try:
                chunk = json.loads(data.decode("utf-8"))
            except ValueError:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            piece = (choices[0].get("delta") or {}).get("content") or ""
            if piece:
                return piece

    def close(self):
        # Closing the response body first is what actually releases
        # the socket; the connection close behind it is housekeeping.
        try:
            self._response.close()
        except Exception:
            pass
        try:
            self._conn.close()
        except Exception:
            pass

    def __del__(self):
        self.close()


class InboxSDK:
    """One provider, the SDK way: ``InboxSDK("atlas").chat.create(...)``."""

    def __init__(self, provider_name):
        if provider_name not in PROVIDERS:
            raise ValueError("unknown provider " + repr(provider_name))
        row = PROVIDERS[provider_name]
        self.provider_name = provider_name
        self.model = row["model"]
        self.base_url = row["base_url"]
        self.chat = _ChatNamespace(self)

    def _open(self, payload):
        parts = urllib.parse.urlparse(self.base_url + "/v1/chat/completions")
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json",
                   "Authorization": "Bearer local-dev-key"}
        conn = http.client.HTTPConnection(
            parts.hostname, parts.port or 80, timeout=30.0
        )
        try:
            conn.request("POST", parts.path, body=body, headers=headers)
            return conn, conn.getresponse()
        except (OSError, http.client.HTTPException) as exc:
            conn.close()
            raise SDKError("request failed: " + str(exc)) from exc


class _ChatNamespace:
    def __init__(self, sdk):
        self._sdk = sdk

    def create(self, messages, temperature=0.2):
        sdk = self._sdk
        start = time.perf_counter()
        conn, response = sdk._open(
            {"model": sdk.model, "messages": messages, "temperature": temperature}
        )
        try:
            raw = response.read().decode("utf-8", errors="replace")
            if response.status != 200:
                raise SDKError(
                    "request failed with status " + str(response.status) + ": " + raw[:200]
                )
            data = json.loads(raw)
            return SDKResponse(
                data["choices"][0]["message"]["content"],
                data.get("usage") or {},
                time.perf_counter() - start,
            )
        finally:
            conn.close()

    def create_stream(self, messages, temperature=0.2, chaos=None):
        sdk = self._sdk
        payload = {
            "model": sdk.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if chaos:
            payload["chaos"] = chaos
        conn, response = sdk._open(payload)
        if response.status != 200:
            raw = response.read().decode("utf-8", errors="replace")
            conn.close()
            raise SDKError(
                "request failed with status " + str(response.status) + ": " + raw[:200]
            )
        return SDKStream(conn, response)
