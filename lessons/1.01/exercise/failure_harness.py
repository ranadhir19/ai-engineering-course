"""Failure harness for the AIE 1.01 hardening exercise.

Usage:
    python3 failure_harness.py [--client PATH]

Default client: the exercise solution next to this file
(exercise/solution/inbox_client.py). Point --client at the unhardened
exercise/inbox_client.py and scenarios 2, 3 and 7 fail by design:
2 and 3 need the retry loop, and 7 isolates the timeout with
max_retries=0, a parameter only the hardened client accepts.

For every scenario the harness starts the mock server (from
../solution/mock_model_server.py) on an ephemeral port in the mode the
scenario needs, imports the client module from the given path, runs one
probe, and asserts on the reply, the exception type, the server's
request count (GET /__count) and the elapsed time. One PASS/FAIL line
per scenario, exit 0 only if all seven pass. Standard library only.
"""

import argparse
import http.client
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLIENT = os.path.join(HERE, "solution", "inbox_client.py")
MOCK_SERVER = os.path.join(HERE, "..", "solution", "mock_model_server.py")
QUESTION = [{"role": "user", "content": "When is the launch?"}]


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def get_count(port):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        conn.request("GET", "/__count")
        response = conn.getresponse()
        return json.loads(response.read().decode("utf-8"))["requests"]
    finally:
        conn.close()


class Server:
    def __init__(self, mode):
        self.port = free_port()
        self.base_url = "http://127.0.0.1:" + str(self.port)
        self.proc = subprocess.Popen(
            [sys.executable, MOCK_SERVER, "--port", str(self.port), "--mode", mode],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("mock server exited early in mode " + mode)
            try:
                get_count(self.port)
                return
            except Exception:
                time.sleep(0.05)
        raise RuntimeError("mock server did not become ready in mode " + mode)

    def count(self):
        return get_count(self.port)

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)


def load_client_module(path, tag):
    spec = importlib.util.spec_from_file_location("client_under_test_" + tag, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_raises(exc_type, fn):
    try:
        fn()
    except exc_type as exc:
        return exc
    raise AssertionError("expected " + exc_type.__name__ + " but nothing was raised")


# -- the seven scenarios ----------------------------------------------------

def scenario_ok(mod, client_path):
    server = Server("ok")
    try:
        client = mod.ModelClient(server.base_url)
        answer = client.chat(QUESTION)
        count = server.count()
        assert isinstance(answer, str) and len(answer) > 0, "empty answer"
        assert "launch" in answer.lower(), "answer does not mention the launch: " + answer
        assert count == 1, "request count " + str(count) + " != 1"
        return "answer_len=" + str(len(answer)) + " requests=" + str(count)
    finally:
        server.stop()


def scenario_ratelimit2(mod, client_path):
    server = Server("ratelimit2")
    try:
        client = mod.ModelClient(server.base_url)
        start = time.monotonic()
        answer = client.chat(QUESTION)
        elapsed = time.monotonic() - start
        count = server.count()
        assert isinstance(answer, str) and len(answer) > 0, "empty answer after retries"
        assert count == 3, "request count " + str(count) + " != 3"
        assert elapsed >= 1.5, "elapsed %.2fs < 1.5s (Retry-After not honoured?)" % elapsed
        return "requests=" + str(count) + " elapsed=%.2fs" % elapsed
    finally:
        server.stop()


def scenario_server_error(mod, client_path):
    server = Server("server_error")
    try:
        client = mod.ModelClient(server.base_url)
        expect_raises(mod.ServerError, lambda: client.chat(QUESTION))
        count = server.count()
        assert count == 4, "request count " + str(count) + " != 4 (1 + 3 retries)"
        return "raised=ServerError requests=" + str(count)
    finally:
        server.stop()


def scenario_bad_request(mod, client_path):
    server = Server("bad_request")
    try:
        client = mod.ModelClient(server.base_url)
        expect_raises(mod.BadRequestError, lambda: client.chat(QUESTION))
        count = server.count()
        assert count == 1, "request count " + str(count) + " != 1 (400 must never be retried)"
        return "raised=BadRequestError requests=" + str(count)
    finally:
        server.stop()


def scenario_auth(mod, client_path):
    server = Server("auth")
    try:
        anon = mod.ModelClient(server.base_url)
        expect_raises(mod.AuthError, lambda: anon.chat(QUESTION))
        count1 = server.count()
        assert count1 == 1, "request count " + str(count1) + " != 1 (401 must never be retried)"
        authed = mod.ModelClient(server.base_url, api_key="test-key-123")
        answer = authed.chat(QUESTION)
        count2 = server.count()
        assert isinstance(answer, str) and len(answer) > 0, "empty answer with a key"
        assert count2 == 2, "request count " + str(count2) + " != 2 after the keyed call"
        return "anon=AuthError requests=" + str(count1) + " keyed=ok requests=" + str(count2)
    finally:
        server.stop()


def scenario_malformed(mod, client_path):
    server = Server("malformed")
    try:
        client = mod.ModelClient(server.base_url)
        expect_raises(mod.MalformedResponseError, lambda: client.chat(QUESTION))
        count = server.count()
        assert count == 1, "request count " + str(count) + " != 1 (malformed must never be retried)"
        return "raised=MalformedResponseError requests=" + str(count)
    finally:
        server.stop()


def scenario_slow(mod, client_path):
    # max_retries=0 isolates the timeout: one attempt, no retry waits.
    # The unhardened client has no max_retries parameter, so constructing
    # it raises TypeError here and this scenario fails for it by design.
    server = Server("slow")
    try:
        client = mod.ModelClient(server.base_url, timeout_s=1.0, max_retries=0)
        start = time.monotonic()
        expect_raises(mod.NetworkError, lambda: client.chat(QUESTION))
        elapsed = time.monotonic() - start
        count = server.count()
        assert elapsed < 10, "elapsed %.2fs >= 10s (timeout not enforced?)" % elapsed
        assert count == 1, "request count " + str(count) + " != 1"
        return "raised=NetworkError requests=" + str(count) + " elapsed=%.2fs" % elapsed
    finally:
        server.stop()


SCENARIOS = [
    ("1 ok", scenario_ok),
    ("2 ratelimit2", scenario_ratelimit2),
    ("3 server_error", scenario_server_error),
    ("4 bad_request", scenario_bad_request),
    ("5 auth", scenario_auth),
    ("6 malformed", scenario_malformed),
    ("7 slow", scenario_slow),
]


def main():
    parser = argparse.ArgumentParser(description="AIE 1.01 failure harness.")
    parser.add_argument("--client", default=DEFAULT_CLIENT, help="path to inbox_client.py under test")
    args = parser.parse_args()
    client_path = os.path.abspath(args.client)
    # A stray key in the environment would silently authenticate the
    # no-key probe in scenario 5; the harness controls this variable.
    os.environ.pop("INBOX_API_KEY", None)

    print("client under test: " + client_path)
    passed = 0
    for tag, fn in SCENARIOS:
        label = tag.replace(" ", "_")
        try:
            mod = load_client_module(client_path, label)
            detail = fn(mod, client_path)
            print("Scenario " + tag + ": PASS (" + detail + ")")
            passed += 1
        except Exception as exc:  # AssertionError and every probe failure
            print("Scenario " + tag + ": FAIL (" + type(exc).__name__ + ": " + str(exc) + ")")
    total = len(SCENARIOS)
    if passed == total:
        print("VERDICT: PASS " + str(passed) + "/" + str(total))
        return 0
    print("VERDICT: FAIL " + str(passed) + "/" + str(total))
    return 1


if __name__ == "__main__":
    sys.exit(main())
