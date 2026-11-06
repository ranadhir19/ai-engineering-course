"""ModelClient + one interface over three providers (Lesson AIE 1.02).

The ModelClient below is the hardened client from Lesson 1.01's
exercise solution, unchanged: same interface, same error mapping, same
retry policy. What 1.02 adds lives entirely in data plus one subclass:

- ``PROVIDERS`` -- a table. Everything that differs between providers
  (base URL, model name, key environment variable, prices, context
  limit) is a row in this table, not a branch in the code.
- ``ProviderClient`` -- a ModelClient bound to one row of the table.
  Its ``chat`` takes no model argument, times the call, converts the
  response's usage into dollars with the row's prices, and re-names
  the two failures a multi-provider caller must be able to see:
  a 400 carrying "context_length_exceeded" becomes
  ``ContextTooLargeError``; a network failure becomes
  ``ProviderUnavailableError`` naming the provider. Nothing is
  silently re-routed: choosing a provider is the caller's decision,
  made in the open.

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


class ContextTooLargeError(ModelError):
    """The prompt exceeds the chosen provider's context limit (HTTP 400
    with code context_length_exceeded). The fix is a bigger provider
    or a smaller prompt -- never a retry."""


class ProviderUnavailableError(ModelError):
    """The chosen provider could not be reached at all. Raised instead
    of silently falling back: a fallback is a policy decision, and
    policies belong to the caller, in the open."""


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
# Lesson 1.02: providers as data, one interface over the table.
# Prices are US dollars per million tokens, input and output priced
# separately, mirroring the mock servers' published tables exactly.
# ---------------------------------------------------------------------

PROVIDERS = {
    "sprout": {
        "base_url": "http://127.0.0.1:8771",
        "model": "sprout-1",
        "key_env": "SPROUT_API_KEY",
        "price_in_per_mtok": 0.15,
        "price_out_per_mtok": 0.30,
        "context_tokens": 600,
    },
    "atlas": {
        "base_url": "http://127.0.0.1:8772",
        "model": "atlas-1",
        "key_env": "ATLAS_API_KEY",
        "price_in_per_mtok": 0.80,
        "price_out_per_mtok": 1.60,
        "context_tokens": 4000,
    },
    "oracle": {
        "base_url": "http://127.0.0.1:8773",
        "model": "oracle-1",
        "key_env": "ORACLE_API_KEY",
        "price_in_per_mtok": 5.00,
        "price_out_per_mtok": 15.00,
        "context_tokens": 20000,
    },
}


def cost_usd(usage, provider_name):
    """Dollars for one exchange: the usage counts, priced by the table.

    (prompt_tokens x input price + completion_tokens x output price)
    / 1,000,000 -- prices are per million tokens.
    """
    row = PROVIDERS[provider_name]
    return (
        usage.get("prompt_tokens", 0) * row["price_in_per_mtok"]
        + usage.get("completion_tokens", 0) * row["price_out_per_mtok"]
    ) / 1_000_000


class ProviderClient(ModelClient):
    """A ModelClient bound to one row of PROVIDERS.

    ``chat(messages)`` needs no model argument -- the provider choice
    carries it. After a successful call, ``last_usage`` (from
    ModelClient), ``last_cost_usd`` and ``last_elapsed_s`` describe
    what the call consumed, in tokens, dollars and seconds.
    """

    def __init__(self, provider_name, timeout_s=10.0, debug=False, max_retries=3):
        if provider_name not in PROVIDERS:
            raise ValueError(
                "unknown provider " + repr(provider_name)
                + "; known: " + ", ".join(sorted(PROVIDERS))
            )
        row = PROVIDERS[provider_name]
        self.provider_name = provider_name
        self.provider = row
        self.model = row["model"]
        api_key = os.environ.get(row["key_env"]) or "local-dev-key"
        super().__init__(
            row["base_url"],
            api_key=api_key,
            timeout_s=timeout_s,
            debug=debug,
            max_retries=max_retries,
        )
        self.last_cost_usd = None
        self.last_elapsed_s = None

    def chat(self, messages, temperature=0.2):
        start = time.perf_counter()
        try:
            text = super().chat(messages, model=self.model, temperature=temperature)
        except BadRequestError as exc:
            if "context_length_exceeded" in str(exc):
                raise ContextTooLargeError(
                    "provider " + self.provider_name + " (" + self.model + ") "
                    "rejected the prompt: " + str(exc)
                ) from exc
            raise
        except NetworkError as exc:
            raise ProviderUnavailableError(
                "provider " + self.provider_name + " (" + self.model + ") "
                "unavailable: " + str(exc)
            ) from exc
        self.last_elapsed_s = time.perf_counter() - start
        self.last_cost_usd = cost_usd(self.last_usage or {}, self.provider_name)
        return text
