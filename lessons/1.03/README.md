# Lesson 1.03 — Tokens & Context Windows

Phase 1 (Inbox Assistant), Lesson 3 of 12.

## Summary

Every number in the course so far — the usage counts, the prices,
the context limits — has been denominated in a unit nobody had
examined: the token. The stand-in servers meter in whitespace
words, a simplification they publish openly. Real providers meter
in subword tokens, and the two meters disagree by a factor that
depends on the text. This lesson builds the real meter — a
byte-pair tokenizer, trained in the open on the course's own
texts — and then builds the discipline the meter makes possible:
a **budgeter inside the client** that counts a prompt before it is
sent, keeps a reserve for the answer, and fits a document set into
a window that cannot hold it all under a stated loss policy, with
**every loss logged**. Everything runs offline, standard library
only, and every number is measured by the pack's own drivers.

## What was built

- `tokenizer.py` — a byte-pair encoder built from first
  principles: pre-tokenise into word/number/punctuation/whitespace
  pieces, start from the 256 bytes, and merge the most frequent
  adjacent pair 1,500 times over a 68-thousand-byte corpus
  (`corpus.txt`: the course's own scripts, READMEs and documents,
  plus the client itself). Deterministic tie-breaking means the
  same corpus trains the same merges on any machine; the merges
  cache to `tokenizer_merges.json`. Measured on this pack: ordinary
  prose counts **2.4 tokens per word** on this meter (a production
  tokenizer, trained on vastly more text with a far larger
  vocabulary, reads lower; the disagreement between meters, and
  its size, is the lesson).
- `budget.py` — the budgeter. `BudgetedProviderClient` counts
  before it sends: prompt tokens plus a stated reserve over the
  window raises `BudgetExceededError` locally, with the numbers in
  the message, before any request exists. `fit_documents` walks
  documents in relevance order and includes each whole while the
  exactly-counted prompt fits the budget; a document that does not
  fit whole is kept as its longest whole-sentence prefix when the
  remaining room is worth using, and every document not included
  whole produces a loss-log entry whose kept + dropped counts sum
  to the document's full count.
- `documents.py` — the fitting problem: five project documents
  (6,447 tokens as blocks) and one question about launch risks and
  their owners, with an auditable relevance ranking (checklist 39,
  brief 14, vendor review 10, support digest 4, status memo 4).
- `count_tokens.py` — the two meters on the same shelf of texts:
  the launch question (5 words, 10 tokens), the 1.02 summary
  prompt (749 words, 1,833 tokens), a JSON usage object (6 words,
  34 tokens), thirty lines of the client as code.
- `run_fitting.py` — the fitting task run both ways against the
  live stand-ins. Naive (all documents, whole): 6,500 tokens —
  refused locally by the budgeted client with zero requests sent,
  and rejected by sprout's 600-token window as
  `ContextTooLargeError`. Fitted under a 3,600-token budget
  (atlas's 4,000 window minus a 400 reserve): **3,569 tokens**,
  sent once, answered; the loss log records the vendor review
  truncated (kept 374, dropped 1,013) and the support digest and
  status memo skipped (1,228 and 688 dropped).

The client from 1.01/1.02 is carried unchanged; the three provider
servers are carried unchanged, word meter and all — the gap
between what the budgeter counts (3,569) and what the server
meters (1,435) is shown, named, and left in the open, because on a
real provider the two meters are the same kind and the budgeter's
number is the one that has to fit.

## How to run everything

From `solution/` (drivers start the three servers themselves):

    python3 count_tokens.py
    python3 run_fitting.py

The first run of anything that counts trains the tokenizer
(about a minute) and caches the merges; later runs are seconds.

The starter folder is where you begin Act 3: it carries the
tokenizer, the documents and the counter driver; the budgeter is
the exercise, and `run_fitting.py` is an exercise-folder concern
until your policy exists — that stop is deliberate.

## The exercise

In `exercise/`: implement the fitting policy in `budget.py`.
Full statement in `exercise/README.md`; the graded starting point
is `exercise/budget.py`, the harness is
`exercise/budget_harness.py`, and the worked answer is in
`exercise/solution/`.

### Measurable pass condition

Run, from `exercise/`:

    python3 budget_harness.py

It must print PASS for all six scenarios and exit 0:

1. **counter_honesty** — the token meter is exact and
   deterministic; the launch question counts 10 tokens; no
   document counts fewer tokens than words.
2. **budget_never_exceeded** — the fitted prompt counts at most
   the 3,600-token budget, is sent exactly once, and the server's
   word-metered usage never exceeds the counted tokens.
3. **loss_log_complete** — every document not included whole has
   exactly one loss entry, and kept + dropped equals its full
   count.
4. **policy_fills** — kept-whole documents are a prefix of the
   relevance ranking; the vendor review is truncated with a useful
   prefix kept; the fitted prompt fills the budget to within 100
   tokens.
5. **fixed_parts** — the system message and the question survive
   verbatim; they are never shed.
6. **naive_and_guard** — the naive prompt counts over budget, is
   refused locally with zero requests sent, and hits sprout's real
   wall as `ContextTooLargeError` in exactly one request.

Against the starter, scenarios 3 and 4 fail and the other four
pass — the instruments are given; the policy, and the accounting
for what it cuts, are the exercise:

    python3 budget_harness.py --budget budget.py
