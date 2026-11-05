"""ModelClient: a tiny chat-completions client built on the standard library only.

Lesson AIE 1.01 -- The Toolkit: Python, JSON & HTTP.
No third-party imports: http.client for the wire, urllib.parse for the URL,
json for the payload, os for the environment, sys for debug output.
"""

import http.client
import json
import os
import sys
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
    """Return the Retry-After header as a number of seconds, or None."""
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

    def __init__(self, base_url, api_key=None, timeout_s=10.0, debug=False):
        self.base_url = base_url.rstrip("/")
        if api_key is None:
            api_key = os.environ.get("INBOX_API_KEY")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.debug = debug
        self.last_usage = None

    # -- internals ---------------------------------------------------------

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

    # -- public API --------------------------------------------------------

    def chat(self, messages, model="inbox-1", temperature=0.2):
        """Send ``messages`` and return the assistant's reply text."""
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
