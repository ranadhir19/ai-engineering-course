# Exercise 1.06 — Assemble the window

The starter's `context.py` in this folder contains the
concatenator exactly as it was found in the wild: everything you
have, in the order you happen to have it, trimmed from wherever
the trimmer happens to cut, with nothing counted and nothing
logged. It is not a straw man. It passes the two control
scenarios — an uncontested question, and an honest abstention in
a comfortable window — and fails the other eight, each failure a
named disease from the lesson. What is broken is not the model.
It is the assembly. That is your exercise.

## The task

Rebuild `assemble(scenario)` in `context.py` until the harness
reports **all four checks on all ten scenarios**, changing only
the policy — the reader (the lesson's stand-in,
`../solution/context_lab.py`, whose rules are printed in its
docstring) and the scenario set are not yours to edit. The
scenario set is `scenarios.json`: each scenario gives your
assembler a question, a token budget, worked examples, retrieved
documents and a conversation history, and states the gold answer.

The four checks, per scenario:

- **budget** — the window you return, counted with the pack's
  BPE counter, is within the scenario's budget;
- **instruction** — the standing instruction (answer only from
  the context; say "I don't know" when you cannot) is present
  in the system message;
- **answer** — the stand-in's answer equals the gold;
- **no silent drop** — every example, document and history turn
  is either visibly present in the window or named in your
  report's `items` with what was done with it.

The failure families are named in the lesson, and the set is
built so each is visible in the report:

- **freshness** — a document states the world as announced; the
  conversation corrected it. If the document speaks last, the
  stale fact wins (correction, stale-doc, room-move);
- **pressure** — when the window overflows, what the trimmer
  cuts decides what the model becomes: cut the instruction and
  it invents figures from its priors (overflow, examples-cost,
  tight-fit);
- **compaction** — the fact that matters is the oldest turn,
  buried under chatter; dropping the oldest loses it, and only
  a compressor that knows what a fact looks like keeps it
  (needle);
- **retrieval** — five documents, two projects, three figures:
  volume is not relevance, and the ranking decides which source
  speaks last (bloat).

## The rules of the road

- Standard library only; the counter and the stand-in come from
  `../solution/` (already importable from the harness).
- `assemble` receives the whole scenario dict and returns
  `(messages, report)`; the report must carry an `items` list
  naming every input item your policy did not include whole.
  It must work for any scenario of this shape, not the ten it
  is graded on — a policy that memorises the set has learned
  the wrong lesson.
- Every exclusion should be a decision you can defend in one
  sentence: what claim the item had, why another claim outranked
  it. That is the difference between an eviction and a
  disappearance.

## How you are graded

    python3 context_harness.py --assembler context.py   # grade YOUR assembler
    python3 context_harness.py                          # grade the worked solution

The harness runs all ten scenarios through the stand-in and
applies the four checks. Exit 0 only at ten of ten.

Run it against the starter first to see the honest baseline —
2 of 10, the two controls — with the failing checks named per
scenario. The worked answer lives in `solution/context.py` in
this folder: it delegates to the lesson's assembler and passes
ten of ten. Try the exercise before you read it; then be able
to explain, in one sentence each, what the pinning bought, what
the example cap bought, what the ranking bought, and what
compaction bought that dropping could not.
