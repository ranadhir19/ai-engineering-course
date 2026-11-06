# Lesson 1.04 — APIs, SDKs & Streaming

Phase 1 (Inbox Assistant), Lesson 4 of 12.

## Summary

Every call so far has arrived as a block: wait, then everything.
This lesson changes the delivery, not the answer. The stand-in
providers learn the one new trick -- the same completion, sent as
a stream of server-sent events when the request asks for it -- and
the client learns to read a stream the way an engineer has to: with
a clock on it, a policy for ending it, and a plan for the day it
breaks. Along the way the lesson audits the thing that wants to
replace the hand-built client -- a small provider SDK, written for
the course so its behaviour can be measured -- and finds the three
things it hides: the first token's arrival time, the partial answer
when a stream fails, and an abort that only works if you know to
ask for it. Everything runs offline, standard library only, and
every number is measured by the pack's own drivers.

## What was built

- `mock_provider_server.py` — the 1.02/1.03 servers plus
  streaming. Generation is now modelled honestly and identically
  for both deliveries: a completion of N words takes the profile's
  latency (the wait for the first token) plus (N − 1) × its
  per-word stream interval to generate. A blocking call waits that
  out in full; a `"stream": true` call sends a role chunk, one
  content chunk per word, a final chunk carrying finish_reason and
  usage, then `[DONE]` -- and the streamed words concatenate to
  exactly the blocking answer. A `"chaos": {"drop_after_chunks": N}`
  test hook cuts the connection mid-stream on demand, and
  `/__stream_stats` reports, per stream, how many chunks the
  server actually wrote and how the stream ended from its side.
- `streaming.py` — the build. `StreamingProviderClient` is the
  1.03 budgeted client (the budgeter still counts before anything
  is sent) plus `stream_chat`, which returns a `StreamResult` --
  text, per-chunk arrival times, time-to-first-token, usage --
  however the stream ends. A stream ends four ways here, and only
  pre-flight errors raise: `completed`, `stop_sequence` (the
  caller's stop text appeared; everything before it is kept),
  `cancelled` (the caller's cancel event fired -- or was already
  set, in which case no request is made at all), and `dropped`
  (the connection closed without `[DONE]`; the partial comes home
  flagged, never dressed as whole). One discipline is written into
  the code where it bites: close the *response*, not just the
  connection, or the hang-up never reaches the wire.
- `sdk_wrap.py` — the SDK that wants the job: `create` and
  `create_stream` in the usual shape, genuinely nicer on the happy
  path, and measurably blind off it. Its response object has no
  time-to-first-token anywhere; its stream keeps no public partial,
  so a mid-stream drop raises `SDKStreamError` with the arrived
  text nowhere on the object; and its stream stays open -- server
  still generating, still billing -- until `close()` is called or
  the object is collected.
- `run_streaming.py` — the measurements, in six sections. The
  launch answer (38 words): blocking, one wait of 0.71 s on atlas;
  streamed, first word at ≈0.16 s. Time-to-first-token by provider:
  sprout 0.30 s, atlas ≈0.15 s, oracle 0.60 s -- generation time is
  identical either way; only the looking changes. The digest (51
  words), stopped at the third email's subject: 32 words kept, the
  server stopped at 37 chunks. The abort on oracle: cancel at 10
  chunks and the server wrote 11–12 and stopped ($0.0001800–1950
  of the full run's $0.0007800); break out of the SDK's loop
  without closing and it wrote all 51 ($0.0007800); `close()` at
  10 and it stopped at 11 ($0.0001800). The drop, cut at 12
  chunks: the raw client holds 12 chunks flagged partial; the SDK
  raises with 0 words recoverable. And the Assistant itself: the
  naive prompt refused locally at 0 requests, the fitted prompt
  (3,569 tokens) streamed to exactly the blocking answer in 33
  chunks.

The client, the budgeter, the tokenizer and the documents are
carried from 1.01–1.03 unchanged; the only carried file that grew
is the server, and only by the delivery this lesson is about.

## How to run everything

From `solution/` (drivers start the three servers themselves):

    python3 run_streaming.py            # all six sections
    python3 run_streaming.py abort      # or one at a time

## The exercise

In `exercise/`: give the stream its termination discipline --
a stop condition, a mid-stream cancellation, and honest drop
handling -- in `streaming.py`. Full statement in
`exercise/README.md`; the graded starting point is
`exercise/streaming.py`, the harness is
`exercise/stream_harness.py`, and the worked answer is in
`exercise/solution/`.

### Measurable pass condition

Run, from `exercise/`:

    python3 stream_harness.py

It must print PASS for all six scenarios and exit 0:

1. **full_stream_integrity** — a finished stream's text equals
   the blocking answer exactly; usage arrives with the final
   chunk; time-to-first-token is measured and less than the total.
2. **stop_condition** — with a stop text, the stream ends by
   policy with everything before it kept, and the server stops
   early too.
3. **mid_stream_cancel** — a cancel after 10 chunks keeps exactly
   those 10, flagged partial, and the server records the hang-up.
4. **cancel_before_first_token** — a cancel that is already set
   costs no request and no wait.
5. **drop_keeps_partial** — a connection cut at 12 chunks returns
   those 12 chunks flagged not-completed; no exception escapes.
6. **budget_guard_first** — the naive prompt is refused locally
   with zero requests sent; the fitted prompt streams in one.

Against the starter, scenarios 2–5 fail and 1 and 6 pass -- the
transport, the counter and the guard are given; every way of
ending a stream except "eventually" is the exercise:

    python3 stream_harness.py --streaming streaming.py
