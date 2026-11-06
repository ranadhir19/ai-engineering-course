# Lesson 1.06 — Context Engineering

Phase 1 (Inbox Assistant), Lesson 6 of 12.

## Summary

Every lesson so far engineered one tenant of the window — the
client, the providers, the budget, the stream, the prompt. This
lesson engineers the window itself: the assembled whole of
instructions, worked examples, retrieved documents and
conversation history that a real call actually sends. Assembled
the way most systems assemble it — concatenation, in field
order, trimmed from wherever the trimmer cuts — the crowd fails
in ways that look like model failures. On this lesson's
ten-scenario pack, the naive concatenator passes 2 of 10: a
correction in the conversation is outvoted by the document it
corrected, a stale vendor figure speaks after the approval, the
oldest turn — carrying the one date that matters — is dropped
under chatter, and when the window overflows the trimmer cuts
the standing instruction itself, after which the model invents
a catering budget from its priors, confidently. The build is
the alternative: an assembler with an explicit budget policy —
instructions and the question pinned, examples capped at a
quarter of the window, documents ranked by relevance with the
strongest speaking last, history compacted by a printed
durability rule instead of dropped — and a report in which
every item is accounted for, so no exclusion is ever silent.
The policy passes 10 of 10. Everything runs offline, standard
library only, against a deterministic stand-in whose rules are
printed in full; every number is measured by the pack's own
drivers.

## What was built

- `context_lab.py` — the stand-in reader for this lesson. The
  earlier providers answer from an inbox; they have nothing to
  say about context, so the lab is a small documented simulator
  of how a production model treats an assembled window: it
  answers from the last sentence that carries the asked fact
  (recency), it abstains only when the standing instruction
  survived assembly, and otherwise it answers from stale priors,
  confidently and without saying it guessed. Its rules are its
  docstring; nothing about it is hidden, which is what makes an
  assembler's score against it meaningful.
- `scenarios.json` — the adversarial conversation pack: ten
  assembly problems over the Project Aurora world of the
  running thread (launch announced November 18 and corrected
  to November 21; budget approved at 48000 dollars against two
  stale 45000s; the design review moved from Room 4B to
  Room 2A; catering never stated anywhere). Two controls, three
  freshness problems, three pressure problems, one compaction
  problem, one retrieval problem — each with its gold answer
  and the disease it is built to expose.
- `context.py` — the build: `assemble()` under policy
  `context@1.0.0`. Count first with the pack's BPE counter and
  hold a reserve for the answer (1.03); pin the instructions
  and the question (an over-budget pin raises
  `BudgetExceededError` before anything is built); cap examples
  at 25% of the usable window; rank documents by the question's
  content words, seat them whole or sentence-truncated, and
  emit weakest-first so the strongest speaks last; give the
  rest to history — newest turns verbatim, older turns
  compacted by `compact_turns`, whose durability rule (a value,
  or a marker of decision or correction) is printed in the
  module. The return value includes the report: every input
  item, exactly once, with its action and its kept and dropped
  tokens.
- `run_context.py` — the measurements, in five sections: the
  anatomy of one assembled window (the correction scenario at
  a 2000-token budget: history 40.8%, examples 33.9%, documents
  14.6%, instructions 9.6%, the question 1.1% — 934 tokens,
  $0.000747 on atlas), the naive-vs-policy run over the pack
  (2 of 10 against 10 of 10, failures named by check), the
  compaction measurement (3941 tokens of history compact to
  246 — 94% — and the needle scenario's one dated sentence
  survives), the price of both assemblers' windows across the
  pack ($0.006121 naive against $0.005498 policy on atlas), and
  the thread: the mock server's three emails as documents over
  a conversation that corrected two of them, answered November
  21, 48000 dollars, Room 2A from windows of about 660 tokens.

The client, providers, budgeter, tokenizer, streaming client
and prompt library are carried from 1.01–1.05 unchanged. The
new surface is the window.

## How to run everything

From `solution/` (no servers needed — the lab is in-process):

    python3 run_context.py            # all five sections
    python3 run_context.py scenarios  # or one at a time

## The exercise

In `exercise/`: assemble the window. `assemble(scenario)` in
`context.py` starts as the concatenator as found; rebuild the
policy until the harness reports all four checks on all ten
scenarios. Full statement in `exercise/README.md`; the graded
starting point is `exercise/context.py`, the harness is
`exercise/context_harness.py`, the scenario set is shared with
the lesson (`exercise/scenarios.json`, identical to
`solution/scenarios.json`), and the worked answer is in
`exercise/solution/`.

### Measurable pass condition

Run, from `exercise/`:

    python3 context_harness.py --assembler context.py

It must report **10 of 10 scenarios passing all four checks**
and exit 0. Against the starter it reports 2 of 10 — the two
controls — with the failing checks named per scenario: the
honest baseline the lesson starts from.
