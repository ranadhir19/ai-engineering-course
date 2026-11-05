"""STARTER SKELETON -- ModelClient for Lesson AIE 1.01.

Same public interface as the solution. Everything imports and runs;
chat() is yours to build, step by step, following the TODOs inside it.
Standard library only: http.client, urllib.parse, json, os, sys.
"""

import http.client  # noqa: F401  (you will need this)
import json  # noqa: F401
import os
import sys  # noqa: F401
import urllib.parse  # noqa: F401


class ModelError(Exception):
    """Base class for every error raised by ModelClient."""


class BadRequestError(ModelError):
    """The server rejected the request itself (HTTP 400)."""


class AuthError(ModelError):
    """Missing or rejected credentials (HTTP 401 / 403)."""


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


class ModelClient:
    def __init__(self, base_url, api_key=None, timeout_s=10.0, debug=False):
        self.base_url = base_url.rstrip("/")
        if api_key is None:
            api_key = os.environ.get("INBOX_API_KEY")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.debug = debug
        self.last_usage = None

    def chat(self, messages, model="inbox-1", temperature=0.2):
        """Send ``messages`` and return the assistant's reply text.

        TODO 1: Build the payload dict: model, messages, temperature.
                Encode it with json.dumps(...).encode("utf-8").
        TODO 2: Parse base_url with urllib.parse.urlparse and open an
                http.client.HTTPConnection to host/port, timeout=timeout_s.
                POST to /v1/chat/completions with header
                Content-Type: application/json, plus
                Authorization: Bearer KEY when self.api_key is set.
        TODO 3: If debug is on, print the request (method, path, headers
                with the key redacted, body) and later the raw response
                status + body, all to sys.stderr.
        TODO 4: Read the response. Wrap connection/timeout/socket failures
                in NetworkError.
        TODO 5: Map the status: 200 parse choices[0].message.content and
                store data["usage"] on self.last_usage (a 200 whose body
                is not that JSON shape raises MalformedResponseError);
                400 BadRequestError; 401/403 AuthError; 429 RateLimitError
                (parse the Retry-After header into retry_after);
                5xx ServerError.
        """
        raise NotImplementedError(
            "ModelClient.chat is the lesson: implement the five TODO steps in "
            "lessons/1.01/starter/inbox_client.py (worked version in solution/)."
        )
