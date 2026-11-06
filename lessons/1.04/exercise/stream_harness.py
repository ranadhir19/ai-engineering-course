"""Stream harness for the AIE 1.04 exercise.

Usage:
    python3 stream_harness.py [--streaming PATH]

Default streaming module: the exercise solution next to this file
(exercise/solution/streaming.py). Point --streaming at the starter
(exercise/streaming.py) and scenarios 2-5 fail by design: the
transport, the counter and the budget guard are given; the
termination discipline -- a stop condition, a mid-stream
cancellation, and a dropped stream kept partial and flagged -- is
the exercise.

The harness starts the three mock provider servers (from
../solution/), runs six scenarios, and asserts on the returned
StreamResult, the servers' stream statistics, and their request
counts. One PASS/FAIL line per scenario; exit 0 only if all six
pass. Standard library only.
"""

import argparse
import importlib.util
import json
import os
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SOLUTION = os.path.join(HERE, "..", "solution")
sys.path.insert(0, SOLUTION)

from budget import BudgetExceededError, fit_documents  # noqa: E402
from documents import doc_block, fixed_messages, load_documents, rank_documents  # noqa: E402
from inbox_client import ProviderClient  # noqa: E402
from mock_provider_server import digest_answer  # noqa: E402
from providers_common import PORTS, ProviderServers, request_count  # noqa: E402

DEFAULT_STREAMING = os.path.join(HERE, "solution", "streaming.py")

WINDOW = 4000
RESERVE = 400
BUDGET = WINDOW - RESERVE

LAUNCH = [{"role": "user", "content": "When does Project Aurora launch?"}]
DIGEST = [{"role": "user", "content": "Summarise the inbox"}]
STOP_TEXT = "Design review meeting rescheduled"

RESULTS = []


def report(ok, label, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ((" -- " + detail) if detail else ""))
    RESULTS.append(ok)


def load_streaming(path):
    spec = importlib.util.spec_from_file_location("streaming_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stream_stats(provider):
    url = "http://127.0.0.1:" + str(PORTS[provider]) + "/__stream_stats"
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))["streams"]


def wait_record(provider, index, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        records = stream_stats(provider)
        if len(records) > index:
            return records[index]
        time.sleep(0.1)
    raise AssertionError("stream record %d never appeared for %s" % (index, provider))


def settle_index(provider):
    """The index the NEXT stream record will land at.

    A server appends a stream's record when the stream ends, which
    can be a beat after the client saw [DONE] -- taking a bare
    length here can point at the previous stream's slot. Wait for
    the count to hold still, then read it.
    """
    while True:
        n = len(stream_stats(provider))
        time.sleep(0.3)
        if len(stream_stats(provider)) == n:
            return n


def first_words(text, n):
    words = text.split(" ")
    return " ".join(words[:n])


def scenario_full_stream_integrity(streaming):
    label = "1 full_stream_integrity: a finished stream is whole, timed, and accounted"
    try:
        blocking = ProviderClient("atlas")
        expected = blocking.chat(LAUNCH)
        client = streaming.StreamingProviderClient("atlas", reserve_tokens=RESERVE)
        r = client.stream_chat(LAUNCH)
        assert r.completed and r.stop_reason == "completed", r
        assert r.text == expected, "streamed text differs from the blocking answer"
        assert r.usage == blocking.last_usage, (r.usage, blocking.last_usage)
        assert r.chunks == r.usage["completion_tokens"], (r.chunks, r.usage)
        assert r.ttft_s is not None and 0 < r.ttft_s < r.elapsed_s, (r.ttft_s, r.elapsed_s)
        report(True, label, "%d chunks; ttft %.2fs of %.2fs total"
               % (r.chunks, r.ttft_s, r.elapsed_s))
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_stop_condition(streaming):
    label = "2 stop_condition: the stream ends at the stop text, by policy, early"
    try:
        full = digest_answer()
        expected = full[: full.index(STOP_TEXT)].rstrip()
        idx = settle_index("atlas")
        client = streaming.StreamingProviderClient("atlas", reserve_tokens=RESERVE)
        r = client.stream_chat(DIGEST, stop=STOP_TEXT)
        assert r.stop_reason == "stop_sequence", r
        assert r.text == expected, "kept text is not the answer up to the stop text"
        assert STOP_TEXT not in r.text
        rec = wait_record("atlas", idx)
        assert rec["chunks_sent"] < rec["total_chunks"], rec
        report(True, label, "kept %d of %d words; server wrote %d chunks"
               % (len(r.text.split()), rec["total_chunks"], rec["chunks_sent"]))
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_mid_stream_cancel(streaming):
    label = "3 mid_stream_cancel: a cancel keeps the partial and hangs up cleanly"
    try:
        idx = settle_index("oracle")
        cancel = threading.Event()

        def stop_at_ten(piece, result):
            if result.chunks >= 10:
                cancel.set()

        client = streaming.StreamingProviderClient("oracle", reserve_tokens=RESERVE)
        r = client.stream_chat(DIGEST, cancel_event=cancel, on_delta=stop_at_ten)
        assert r.stop_reason == "cancelled", r
        assert not r.completed
        assert r.chunks == 10, r.chunks
        assert r.text == first_words(digest_answer(), 10), "partial text mismatch"
        rec = wait_record("oracle", idx)
        assert rec["outcome"] == "client_disconnected", rec
        assert rec["chunks_sent"] <= r.chunks + 2, rec
        report(True, label, "10 chunks kept; server wrote %d and saw the hang-up"
               % rec["chunks_sent"])
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_cancel_before_first_token(streaming):
    label = "4 cancel_before_first_token: a set cancel costs no request and no wait"
    try:
        cancel = threading.Event()
        cancel.set()
        before = request_count("atlas")
        client = streaming.StreamingProviderClient("atlas", reserve_tokens=RESERVE)
        r = client.stream_chat(LAUNCH, cancel_event=cancel)
        assert r.stop_reason == "cancelled", r
        assert r.chunks == 0 and r.text == "", r
        assert r.elapsed_s < 1.0, r.elapsed_s
        assert request_count("atlas") - before == 0, "a request was sent anyway"
        report(True, label, "0 chunks, 0 requests, %.3fs" % r.elapsed_s)
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_drop_keeps_partial(streaming):
    label = "5 drop_keeps_partial: a cut connection leaves the partial in hand, flagged"
    try:
        client = streaming.StreamingProviderClient("atlas", reserve_tokens=RESERVE)
        r = client.stream_chat(DIGEST, chaos={"drop_after_chunks": 12})
        assert not r.completed, r
        assert r.stop_reason == "dropped", r
        assert r.chunks == 12, r.chunks
        assert r.text == first_words(digest_answer(), 12), "partial text mismatch"
        report(True, label, "12 chunks kept, completed=False, no exception")
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_budget_guard_first(streaming):
    label = "6 budget_guard_first: the budgeter still stands in front of the stream"
    try:
        documents = load_documents()
        naive = fixed_messages([doc_block(d["name"], d["text"]) for d in documents])
        fitted, _losses = fit_documents(rank_documents(documents), BUDGET)
        client = streaming.StreamingProviderClient("atlas", reserve_tokens=RESERVE)
        before = request_count("atlas")
        try:
            client.stream_chat(naive)
            raise AssertionError("an over-budget prompt was streamed")
        except BudgetExceededError:
            pass
        assert request_count("atlas") - before == 0, "the guard sent a request"
        r = client.stream_chat(fitted)
        assert r.completed, r
        assert request_count("atlas") - before == 1
        report(True, label, "naive refused at 0 requests; fitted streamed in 1")
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def main():
    parser = argparse.ArgumentParser(description="AIE 1.04 stream harness.")
    parser.add_argument("--streaming", default=DEFAULT_STREAMING)
    args = parser.parse_args()
    streaming = load_streaming(args.streaming)
    print("streaming module under test: " + args.streaming)

    with ProviderServers():
        scenario_full_stream_integrity(streaming)
        scenario_stop_condition(streaming)
        scenario_mid_stream_cancel(streaming)
        scenario_cancel_before_first_token(streaming)
        scenario_drop_keeps_partial(streaming)
        scenario_budget_guard_first(streaming)

    passed = sum(RESULTS)
    print("RESULT: %d/%d scenarios passed" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) == 6 else 1


if __name__ == "__main__":
    sys.exit(main())
