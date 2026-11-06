# Exercise 1.03 — Fit the documents: a policy, and a log of what it cut

The instruments are given. `tokenizer.count_tokens` (in
`../solution/`) counts a prompt the way a real meter would, and
`BudgetedProviderClient` already refuses — locally, before any
request — a prompt whose count plus its reserve exceeds the
window. What no library can give you is the policy: **which
documents earn their place in a window that cannot hold them all,
and what happens to the ones that do not.** That policy is this
exercise, and like every policy in this course it is graded by a
harness, not by taste.

## The task

In `budget.py` in this folder, implement `fit_documents(documents,
budget_tokens)` under exactly this policy:

1. Walk the documents **in the order given** — the caller ranks
   them (`documents.rank_documents`: relevance to the question,
   ties in pack order). Your function keeps the order it is given.
2. Include a document **whole** while the assembled prompt —
   counted exactly with `count_messages_tokens`, fixed parts
   included — stays within `budget_tokens`.
3. A document that does not fit whole: keep its **longest
   whole-sentence prefix** that fits, if the room remaining is at
   least `MIN_USEFUL_TOKENS` (120); otherwise **skip** it. A
   document is never cut mid-sentence: a truncation a reader
   cannot see is a truncation nobody decided.
4. The system message and the question are **never shed**, however
   tight the budget.
5. Return `(messages, losses)`: one loss entry per document not
   included whole —
   `{"document", "action", "kept_tokens", "dropped_tokens"}` with
   action `"truncated"` or `"skipped"`, and kept + dropped equal
   to the document block's full token count
   (`count_tokens(doc_block(name, text))`).

Rules of the road:

- Count exactly; never estimate-and-hope. Assemble the candidate
  prompt and count it whole — a budget checked with an estimate
  leaks by the size of the estimate.
- No silent loss anywhere: if it is not in the prompt whole, it
  is in the log. A document that vanishes without an entry is
  this course's definition of a bug.
- Standard library only; the tokenizer, documents and client come
  from `../solution/` (already importable).

## How you are graded

    python3 budget_harness.py

The harness starts the three provider servers and asserts on
counted tokens, loss-log completeness, the relevance order,
server request counts (via `/__count`) and exception types. The
fitting target throughout: atlas's window of 4,000 tokens with a
400-token reserve for the answer — a prompt budget of **3,600**:

1. `counter_honesty` — the meter is exact and deterministic; the
   launch question counts 10 tokens; tokens never run below words.
2. `budget_never_exceeded` — fitted prompt at most 3,600 counted
   tokens, sent exactly once; the server's word-metered usage
   stays at or below the counted tokens.
3. `loss_log_complete` — every cut logged exactly once, and the
   log's kept + dropped equals each document's full count.
4. `policy_fills` — kept-whole documents form a prefix of the
   relevance ranking; the vendor review is truncated with at
   least 300 tokens kept; the fitted prompt reaches within 100
   tokens of the budget.
5. `fixed_parts` — system message and question verbatim.
6. `naive_and_guard` — the all-documents prompt counts 6,500,
   over budget; the budgeted client refuses it with zero requests
   sent; sprout rejects it as `ContextTooLargeError` in exactly
   one request.

Exit 0 with 6/6 PASS is a pass. Run it against the starter first
to see the honest baseline — scenarios 3 and 4 fail there:

    python3 budget_harness.py --budget budget.py

The worked answer lives in `solution/budget.py` in this folder.
Try the exercise before you read it; then be able to explain, in
one sentence, why the budget is stated in the tokenizer's tokens
and not in the server's words.
