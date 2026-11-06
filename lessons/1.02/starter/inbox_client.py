"""Hardened ModelClient from Lesson 1.01 -- the 1.02 starting point.

This is 1.01's exercise solution (identical interface and error
mapping to the base client in lessons/1.01/solution/inbox_client.py,
plus one new constructor parameter, ``max_retries`` (default 3), and
retry with exponential backoff:

- Only RateLimitError and ServerError are retried. BadRequestError,
  AuthError, MalformedResponseError and NetworkError are raised at once:
  retrying them cannot change the answer.
- Backoff starts at 0.5 s and doubles after every failed attempt.
- A Retry-After value on a 429 replaces the backoff for that wait when
  it is longer (the server's instruction wins).

Standard library only.
"""

import http.client
import json
import os
import sys
import time
import urllib.parse


class ModelError(Exception):
    """Base class for every error raised by ModelClient."""


class BadRequestError(ModelError):
    """The server rejected the request itself (HTTP 400). Retrying will not help."""


class AuthError(ModelError):
    """Missing or rejected credentials (HTTP 401 / 403). Retrying will not help."""


class RateLimitError(ModelError):
    """Too many requests (HTTP 429). ``retry_after`` is seconds, or None."""

    def __init__(self, message="rate limited", retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class ServerError(ModelError):
    """The server failed while handling a valid request (HTTP 5xx)."""


class NetworkError(ModelError):
    """No usable HTTP response at all: refused, timed out, or a socket error."""


class MalformedResponseError(ModelError):
    """HTTP 200 arrived, but the body was not the JSON shape we were promised."""


def _parse_retry_after(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ModelClient:
    """Speak to any endpoint that accepts chat-completions shaped JSON."""

    def __init__(self, base_url, api_key=None, timeout_s=10.0, debug=False, max_retries=3):
        self.base_url = base_url.rstrip("/")
        if api_key is None:
            api_key = os.environ.get("INBOX_API_KEY")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.debug = debug
        self.max_retries = max_retries
        self.last_usage = None

    def _debug(self, text):
        if self.debug:
            print(text, file=sys.stderr)

    def _post_chat(self, payload):
        """Send one POST and return (status, headers_dict, body_text)."""
        url = self.base_url + "/v1/chat/completions"
        parts = urllib.parse.urlparse(url)
        path = parts.path
        if parts.query:
            path = path + "?" + parts.query
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key

        shown = dict(headers)
        if "Authorization" in shown:
            shown["Authorization"] = "Bearer ***REDACTED***"
        self._debug(">>> POST " + path)
        self._debug(">>> headers: " + json.dumps(shown, sort_keys=True))
        self._debug(">>> body: " + body.decode("utf-8"))

        if parts.scheme == "https":
            conn = http.client.HTTPSConnection(
                parts.hostname, parts.port or 443, timeout=self.timeout_s
            )
        else:
            conn = http.client.HTTPConnection(
                parts.hostname, parts.port or 80, timeout=self.timeout_s
            )
        try:
            conn.request("POST", path, body=body, headers=headers)
            response = conn.getresponse()
            raw = response.read()
            status = response.status
            resp_headers = {k.lower(): v for k, v in response.getheaders()}
        except (OSError, http.client.HTTPException) as exc:
            raise NetworkError("network error talking to " + self.base_url + ": " + str(exc)) from exc
        finally:
            conn.close()

        text = raw.decode("utf-8", errors="replace")
        self._debug("<<< status: " + str(status))
        self._debug("<<< body: " + text)
        return status, resp_headers, text

    def _chat_once(self, messages, model, temperature):
        payload = {"model": model, "messages": messages, "temperature": temperature}
        status, headers, text = self._post_chat(payload)

        if status == 200:
            try:
                data = json.loads(text)
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise TypeError("content is not a string")
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise MalformedResponseError(
                    "200 response was not the expected chat-completion JSON: " + str(exc)
                ) from exc
            usage = data.get("usage")
            self.last_usage = usage if isinstance(usage, dict) else {}
            return content
        if status == 400:
            raise BadRequestError("400 bad request: " + text[:200])
        if status in (401, 403):
            raise AuthError(str(status) + " authentication failed: " + text[:200])
        if status == 429:
            raise RateLimitError(
                "429 rate limited: " + text[:200],
                retry_after=_parse_retry_after(headers.get("retry-after")),
            )
        if 500 <= status <= 599:
            raise ServerError(str(status) + " server error: " + text[:200])
        raise ModelError("unexpected HTTP status " + str(status) + ": " + text[:200])

    def chat(self, messages, model="inbox-1", temperature=0.2):
        """Send ``messages``; retry transient failures; return reply text."""
        backoff = 0.5
        attempts = 0
        while True:
            try:
                return self._chat_once(messages, model, temperature)
            except (RateLimitError, ServerError) as exc:
                if attempts >= self.max_retries:
                    raise
                delay = backoff
                if isinstance(exc, RateLimitError) and exc.retry_after is not None:
                    delay = max(delay, float(exc.retry_after))
                self._debug(
                    "<<< retry " + str(attempts + 1) + " in " + str(delay) + "s after "
                    + type(exc).__name__
                )
                time.sleep(delay)
                backoff *= 2
                attempts += 1


# ---------------------------------------------------------------------
# Lesson 1.02 -- YOUR STEPS (this file is the Act 3 starting point;
# the client above is the hardened 1.01 client, unchanged):
#
#   1. Add the PROVIDERS table: one row per provider with base_url,
#      model, key_env, price_in_per_mtok, price_out_per_mtok and
#      context_tokens. Everything that differs is data.
#   2. Add cost_usd(usage, provider_name): the exchange's usage
#      counts priced by the table, per million tokens.
#   3. Add ProviderClient(ModelClient): bound to one row; chat()
#      needs no model argument, times the call, and sets
#      last_cost_usd / last_elapsed_s after each success.
#   4. Add the two new exceptions and the re-naming: a 400 carrying
#      "context_length_exceeded" becomes ContextTooLargeError; a
#      NetworkError becomes ProviderUnavailableError naming the
#      provider. No silent fallback.
#
# The worked build is in ../solution/inbox_client.py. Build yours
# first; compare after.
# ---------------------------------------------------------------------
