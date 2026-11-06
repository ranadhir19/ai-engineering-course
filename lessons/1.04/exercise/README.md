# Exercise 1.04 — End the stream on purpose: stop, cancel, survive the drop

The transport is given. The starter's `streaming.py` in this
folder opens the stream behind the 1.03 budget guard, parses the
server-sent events, assembles the text and times every chunk --
a stream that nothing interrupts completes correctly through it.
What no library can give you is the discipline for the other
three ways a stream can end, because all three are policy:
**when to stop reading, how to stop early, and what a partial
answer is worth.** That discipline is this exercise, and like
every policy in this course it is graded by a harness, not by
taste.

## The task

In `streaming.py` in this folder, implement the termination
discipline of `stream_chat` under exactly these rules:

1. **Stop condition.** When the caller's `stop` text appears in
   the accumulated answer, keep everything before it (the stop
   text itself is not part of the answer), hang up, and end with
   `stop_reason == "stop_sequence"` and `completed == False`.
   The check runs as chunks arrive, including a stop text that
   spans a chunk boundary.
2. **Mid-stream cancellation.** The caller's `cancel_event` (a
   `threading.Event`) is checked as chunks arrive; when it fires,
   keep the chunks already received, hang up, and end with
   `stop_reason == "cancelled"` and `completed == False`. A
   cancel that is already set before the call must cost nothing:
   no request is sent, no time is waited out, and the result is
   an empty cancellation.
3. **The drop.** If the connection closes without `[DONE]`, do
   not raise and do not call it finished: return the partial with
   `completed == False` and `stop_reason == "dropped"`. A partial
   answer presented as a whole one is this course's definition of
   a bug -- it is exactly what the starter does now.
4. **Hang up so the server notices.** Closing the connection
   object is not enough -- the response body holds the socket's
   file open. Close the response as well, or the server keeps
   generating (and billing) into a connection nobody reads.
   The harness reads the server's own stream statistics: after
   your stop or cancel, its `chunks_sent` must stop within two
   chunks of what you consumed.

The happy path and the guard do not change: a finished stream
still returns the whole answer with its usage and timings, and
an over-budget prompt is still refused before any request.

Rules of the road:

- Standard library only; the client, budgeter, tokenizer and
  servers come from `../solution/` (already importable).
- Never a bare exception for a mid-stream event, and never a
  silent truncation: every ending is named in `stop_reason`.

## How you are graded

    python3 stream_harness.py

The harness starts the three provider servers (from
`../solution/`) and asserts on the returned `StreamResult`, the
servers' `/__stream_stats` records, and their request counts:

1. `full_stream_integrity` — the streamed launch answer equals
   the blocking answer exactly; usage matches the blocking
   call's; chunks equal the completion's word count; a
   time-to-first-token is measured, strictly inside the total.
2. `stop_condition` — the digest, stopped at "Design review
   meeting rescheduled": the kept text is exactly the answer
   before the stop text (32 of 51 words), and the server's record
   shows it stopped early too.
3. `mid_stream_cancel` — the oracle digest, cancelled after 10
   chunks: exactly those 10 kept and flagged; the server's record
   says `client_disconnected` with at most 12 chunks written.
4. `cancel_before_first_token` — the cancel already set: 0
   chunks, 0 requests sent, back in under a second.
5. `drop_keeps_partial` — the atlas digest with the server's
   chaos hook cutting at 12 chunks: those 12 returned,
   `completed == False`, `stop_reason == "dropped"`, and no
   exception escapes.
6. `budget_guard_first` — the naive prompt raises
   `BudgetExceededError` with the atlas request count unmoved;
   the fitted prompt streams to completion in exactly one
   request.

Exit 0 with 6/6 PASS is a pass. Run it against the starter first
to see the honest baseline -- scenarios 2–5 fail there, because
the starter's stream can only end one way:

    python3 stream_harness.py --streaming streaming.py

The worked answer lives in `solution/streaming.py` in this
folder. Try the exercise before you read it; then be able to
explain, in one sentence, why closing the connection object alone
does not hang up on the server.
