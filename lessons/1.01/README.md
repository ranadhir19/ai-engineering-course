# Lesson 1.01 — The Toolkit: Python, JSON & HTTP

Phase 1 (Inbox Assistant), Lesson 1 of 12.

## Summary

Before any framework, any SDK or any live API, there are three things
every AI engineer actually does all day: hold data as JSON, send it
over HTTP, and deal with what comes back — including when what comes
back is an error. This lesson builds that whole loop by hand, using
nothing but the Python standard library, against a local mock server
that behaves like a real chat-completions endpoint: same request
shape, same response shape, same failure modes, fully deterministic
and offline.

## What was built

- `mock_model_server.py` — a mock model endpoint on
  `http.server.ThreadingHTTPServer`. In its normal mode it answers
  questions extractively from a built-in inbox of three short emails
  (a project launch, a budget approval, a meeting reschedule): it
  scores the emails by keyword overlap with your last user message and
  returns the best email's relevant sentences. Its other modes
  reproduce the failures a real endpoint produces: missing auth,
  rate limiting, server errors, bad requests, malformed bodies, and
  responses that never arrive in time.
- `inbox_client.py` — `ModelClient`, a small client for that endpoint
  built on `http.client` and `urllib.parse` only. One method,
  `chat(messages)`, returns the assistant's reply text and stores the
  response's usage numbers on `client.last_usage`. Every failure is a
  typed exception: `BadRequestError`, `AuthError`, `RateLimitError`
  (carrying `retry_after`), `ServerError`, `NetworkError`, and
  `MalformedResponseError`, all under a common `ModelError` base.
  With `debug=True` the client prints the raw request (API key
  redacted) and the raw response to stderr — the wire, made visible.
- `ask.py` — a driver that asks the inbox a question and prints the
  answer.
- `summarise_notes.py` (solution, Act 4) — reads `meeting_notes.txt`,
  sends it as a system + user message pair asking for a summary, and
  prints the result.

## How to run everything

Terminal 1, from either `starter/` or `solution/`:

    python3 mock_model_server.py --port 8765 --mode ok

Terminal 2, same folder:

    python3 ask.py
    python3 summarise_notes.py        (solution folder only)

Try the other server modes (`auth`, `ratelimit2`, `server_error`,
`bad_request`, `malformed`, `slow`) and watch the client raise the
matching exception for each. Add `debug=True` to the client in a
scratch copy and read the actual bytes.

The starter folder is where you begin: its `inbox_client.py` is a
skeleton with the same public interface and five guided TODO steps
inside `chat()`. Its `ask.py` fails with a `NotImplementedError`
pointing at those steps — that failure is the starting line, not a bug.

## The exercise

In `exercise/`: harden the client. Add retry with exponential backoff
for the two failures that can heal — `RateLimitError` and
`ServerError` — and never retry the ones that cannot. Full statement
in `exercise/README.md`; the graded starting point is
`exercise/inbox_client.py`, an unmodified copy of the solution client,
and the worked answer is in `exercise/solution/`.

### Measurable pass condition

Run, from `exercise/`:

    python3 failure_harness.py

It must print PASS for all seven scenarios and exit 0:

1. **ok** — a normal question returns a non-empty answer mentioning
   the launch, in exactly 1 request.
2. **ratelimit2** — two 429s then success: the call succeeds, the
   server saw exactly 3 requests, and at least 1.5 s elapsed, proving
   the Retry-After wait (or equivalent backoff) really happened.
3. **server_error** — a persistent 500 raises `ServerError` after
   exactly 4 requests: 1 attempt + 3 retries.
4. **bad_request** — a 400 raises `BadRequestError` after exactly
   1 request: never retried.
5. **auth** — no key against an auth-requiring server raises
   `AuthError` after exactly 1 request; the same server with a key
   answers normally (2 requests total).
6. **malformed** — a 200 with a non-JSON body raises
   `MalformedResponseError` after exactly 1 request: never retried.
7. **slow** — a server that sleeps 30 s, called with a 1-second
   timeout and retries disabled, raises `NetworkError` in under 10 s.

Point the same harness at the unhardened starting client and it fails
scenarios 2, 3 and 7 — that contrast is the lesson:

    python3 failure_harness.py --client inbox_client.py
