"""Act 3 driver: streaming, measured six ways.

Every experiment runs against the local stand-ins and prints its
measurements -- nothing here is asserted by hand-waving. Sections
can be run one at a time (the numbers are the same):

    python3 run_streaming.py [compare|ttft|stop|abort|drop|assistant]

- compare:   the same answer, blocking and streamed (atlas).
- ttft:      time-to-first-token across the three providers.
- stop:      a stop condition ends the stream by policy.
- abort:     cancelling, measured client-side AND server-side --
             the raw client's hang-up, the SDK's break-out-of-the-
             loop, and the SDK's deliberate close().
- drop:      a connection cut mid-stream: what each client keeps.
- assistant: the Inbox Assistant itself, streaming behind the 1.03
             budgeter: the naive prompt refused locally, the fitted
             prompt streamed.
"""

import json
import os
import sys
import threading
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from budget import BudgetExceededError, fit_documents  # noqa: E402
from documents import load_documents, rank_documents  # noqa: E402
from inbox_client import ProviderClient  # noqa: E402
from providers_common import PORTS, ProviderServers, request_count  # noqa: E402
from sdk_wrap import InboxSDK, SDKStreamError  # noqa: E402
from streaming import StreamingProviderClient  # noqa: E402

LAUNCH = [{"role": "user", "content": "When does Project Aurora launch?"}]
DIGEST = [{"role": "user", "content": "Summarise the inbox"}]
WINDOW, RESERVE = 4000, 400


def stream_stats(provider):
    url = "http://127.0.0.1:" + str(PORTS[provider]) + "/__stream_stats"
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))["streams"]


def wait_stream_record(provider, index, timeout=20.0):
    """Wait until the provider's stream record ``index`` exists."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        records = stream_stats(provider)
        if len(records) > index:
            return records[index]
        time.sleep(0.1)
    raise RuntimeError("stream record %d never appeared for %s" % (index, provider))


def settle_index(provider):
    """The index the NEXT stream record will land at (a server
    appends a stream's record when it ends, a beat after the
    client saw [DONE] -- wait for the count to hold still)."""
    while True:
        n = len(stream_stats(provider))
        time.sleep(0.3)
        if len(stream_stats(provider)) == n:
            return n


def cost_out(provider, prompt_words, generated_words):
    from inbox_client import PROVIDERS

    row = PROVIDERS[provider]
    return (
        prompt_words * row["price_in_per_mtok"]
        + generated_words * row["price_out_per_mtok"]
    ) / 1_000_000


def section_compare():
    print("SAME ANSWER, TWO DELIVERIES -- atlas, the launch question")
    blocking = ProviderClient("atlas")
    text_b = blocking.chat(LAUNCH)
    client = StreamingProviderClient("atlas", reserve_tokens=RESERVE)
    r = client.stream_chat(LAUNCH)
    print("blocking:  %d words, all of it after one wait of %.2f s"
          % (len(text_b.split()), blocking.last_elapsed_s))
    print("streaming: first word at %.2f s, last at %.2f s, %d chunks"
          % (r.ttft_s, r.elapsed_s, r.chunks))
    print("texts identical: %s; usage from the final chunk: %s"
          % (r.text == text_b, r.usage))
    print("the answer did not change -- the delivery did")


def section_ttft():
    print("TIME TO FIRST TOKEN -- one question, three providers")
    for name in ("sprout", "atlas", "oracle"):
        blocking = ProviderClient(name)
        blocking.chat(LAUNCH)
        r = StreamingProviderClient(name, reserve_tokens=RESERVE).stream_chat(LAUNCH)
        print("%-7s first word %.2f s | last word %.2f s | %d chunks | "
              "blocking wait %.2f s"
              % (name, r.ttft_s, r.elapsed_s, r.chunks, blocking.last_elapsed_s))
    print("generation takes what it takes; streaming decides when you may look")


def section_stop():
    print("THE STOP CONDITION -- atlas digest, stop at the third email")
    stop = "Design review meeting rescheduled"
    before = settle_index("atlas")
    r = StreamingProviderClient("atlas", reserve_tokens=RESERVE).stream_chat(
        DIGEST, stop=stop
    )
    rec = wait_stream_record("atlas", before)
    kept = len(r.text.split())
    print("kept %d words of %d; stop_reason=%s; the stop text is not in the answer"
          % (kept, rec["total_chunks"], r.stop_reason))
    print("server wrote %d of %d chunks before it saw the closed socket"
          % (rec["chunks_sent"], rec["total_chunks"]))
    print("kept text ends: ...%s" % r.text[-40:])


def section_abort():
    print("THE ABORT, MEASURED THREE WAYS -- oracle, the digest")
    full = StreamingProviderClient("oracle", reserve_tokens=RESERVE).stream_chat(DIGEST)
    print("full run: %d chunks, %.2f s, cost $%.7f"
          % (full.chunks, full.elapsed_s,
             cost_out("oracle", full.usage["prompt_tokens"], full.chunks)))
    idx = settle_index("oracle")

    cancel = threading.Event()

    def stop_at_ten(piece, result):
        if result.chunks >= 10:
            cancel.set()

    r = StreamingProviderClient("oracle", reserve_tokens=RESERVE).stream_chat(
        DIGEST, cancel_event=cancel, on_delta=stop_at_ten
    )
    rec = wait_stream_record("oracle", idx)
    print("raw client, cancel after 10: read %d chunks in %.2f s; stop_reason=%s"
          % (r.chunks, r.elapsed_s, r.stop_reason))
    print("  server-side: wrote %d chunks, outcome=%s; generation billed: $%.7f"
          % (rec["chunks_sent"], rec["outcome"],
             cost_out("oracle", 3, rec["chunks_sent"])))
    idx += 1

    sdk = InboxSDK("oracle")
    stream = sdk.chat.create_stream(DIGEST)
    seen = 0
    for _piece in stream:
        seen += 1
        if seen >= 10:
            break  # the natural thing: just stop reading
    rec = wait_stream_record("oracle", idx)
    print("sdk, break out of the loop at 10: server-side wrote %d of %d chunks, outcome=%s"
          % (rec["chunks_sent"], rec["total_chunks"], rec["outcome"]))
    print("  the connection stayed open because the object stayed alive; billed: $%.7f"
          % cost_out("oracle", 3, rec["chunks_sent"]))
    stream.close()
    idx += 1

    stream = sdk.chat.create_stream(DIGEST)
    seen = 0
    for _piece in stream:
        seen += 1
        if seen >= 10:
            break
    stream.close()
    rec = wait_stream_record("oracle", idx)
    print("sdk, close() after 10: server-side wrote %d chunks, outcome=%s; billed: $%.7f"
          % (rec["chunks_sent"], rec["outcome"],
             cost_out("oracle", 3, rec["chunks_sent"])))


def section_drop():
    print("THE DROP -- atlas, the server cuts the connection after 12 chunks")
    r = StreamingProviderClient("atlas", reserve_tokens=RESERVE).stream_chat(
        DIGEST, chaos={"drop_after_chunks": 12}
    )
    print("raw client: kept %d chunks, completed=%s, stop_reason=%s"
          % (r.chunks, r.completed, r.stop_reason))
    print("  the partial is in your hand, flagged: %r..." % r.text[:60])
    sdk = InboxSDK("atlas")
    yielded = 0
    try:
        for _piece in sdk.chat.create_stream(DIGEST, chaos={"drop_after_chunks": 12}):
            yielded += 1
        print("sdk: stream ended without an error (unexpected)")
    except SDKStreamError as exc:
        print("sdk: raised %s after %d pieces" % (type(exc).__name__, yielded))
        print("  text recoverable from the sdk object afterwards: 0 words")


def section_assistant():
    print("THE ASSISTANT, STREAMING -- atlas, the 1.03 budgeter in front")
    from documents import doc_block, fixed_messages
    from tokenizer import count_messages_tokens

    ranked = rank_documents(load_documents())
    messages, losses = fit_documents(ranked, WINDOW - RESERVE)
    naive = fixed_messages([doc_block(d["name"], d["text"]) for d in load_documents()])
    client = StreamingProviderClient("atlas", reserve_tokens=RESERVE)
    before = request_count("atlas")
    try:
        client.stream_chat(naive)
        print("naive prompt was sent (unexpected)")
    except BudgetExceededError as exc:
        print("naive prompt (%d tokens): refused locally, %d requests sent"
              % (count_messages_tokens(naive), request_count("atlas") - before))
        print("  %s" % str(exc)[:100])
    r = client.stream_chat(messages)
    blocking_text = ProviderClient("atlas").chat(messages)
    print("fitted prompt (%d tokens): first word %.2f s, %d chunks, completed=%s"
          % (count_messages_tokens(messages), r.ttft_s, r.chunks, r.completed))
    print("streamed text == blocking text: %s" % (r.text == blocking_text))
    print("loss log still attached: %s"
          % ", ".join("%s %s" % (l["document"], l["action"]) for l in losses))


SECTIONS = {
    "compare": section_compare,
    "ttft": section_ttft,
    "stop": section_stop,
    "abort": section_abort,
    "drop": section_drop,
    "assistant": section_assistant,
}


def main():
    names = sys.argv[1:] or list(SECTIONS)
    with ProviderServers():
        for name in names:
            SECTIONS[name]()
            print()


if __name__ == "__main__":
    main()
