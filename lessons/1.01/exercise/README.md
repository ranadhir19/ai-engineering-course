# Exercise 1.01 — Harden the client: retries that know when to stop

You start from `inbox_client.py` in this folder: an unmodified copy of
the lesson's solution client. It already has a configurable timeout
(`timeout_s`) and the full typed-error mapping. What it does not have
is any patience — and indiscriminate patience is as bad as none.

## The task

Add retry with exponential backoff to `ModelClient.chat`, under
exactly these rules:

- **Retry only `RateLimitError` and `ServerError`.** These are the
  failures that can heal while you wait.
- **Never retry `BadRequestError`, `AuthError` or
  `MalformedResponseError`.** The request is wrong, the credentials
  are wrong, or the reply is unparseable; sending it again changes
  nothing and costs a request. (`NetworkError` is likewise raised
  immediately — a timeout already waited, and a refused connection
  gets its answer from the caller, not from a silent loop.)
- Add a constructor parameter `max_retries` with default **3**:
  at most 1 initial attempt + 3 retries.
- Backoff starts at **0.5 s** and **doubles** after each failed
  attempt (0.5, 1.0, 2.0).
- On a 429, **honour `Retry-After`** when the error carries one
  (`RateLimitError.retry_after`): if it asks for a longer wait than
  the current backoff, wait that long instead.
- After the retries are exhausted, raise the last error unchanged.
- Keep everything else identical: same method signatures, same status
  mapping, same `last_usage` behaviour, same exceptions, standard
  library only.

## How you are graded

    python3 failure_harness.py

The harness starts the mock server fresh for each of seven scenarios
and asserts on the reply, the exception, the elapsed time, and the
exact number of requests the server received (via its `/__count`
endpoint):

1. `ok` — succeeds in 1 request.
2. `ratelimit2` — succeeds, exactly 3 requests, at least 1.5 s elapsed.
3. `server_error` — raises `ServerError`, exactly 4 requests.
4. `bad_request` — raises `BadRequestError`, exactly 1 request.
5. `auth` — keyless raises `AuthError` in 1 request; with a key it
   succeeds (2 requests total).
6. `malformed` — raises `MalformedResponseError`, exactly 1 request.
7. `slow` — with `timeout_s=1.0` and `max_retries=0`, raises
   `NetworkError` in under 10 s.

Exit 0 with 7/7 PASS is a pass. Run it against your starting point
first to see the honest baseline — scenarios 2, 3 and 7 fail there:

    python3 failure_harness.py --client inbox_client.py

The worked answer lives in `solution/inbox_client.py` in this folder.
Try the exercise before you read it; then diff your version against
it and be able to explain every difference.
