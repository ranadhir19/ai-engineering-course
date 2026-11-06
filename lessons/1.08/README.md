# Lesson 1.08 — Structured Outputs

Phase 1 (Inbox Assistant), Lesson 8 of 12.

## Summary

Every lesson so far engineered what goes into the call and
how it comes back as a stream of words. The words themselves
arrived as prose and were consumed on hope: the Assistant's
triage files a label it parses strictly (1.05), but the
digest and the router need a record — label, priority, a
one-line summary, whether a reply is needed, a due date —
and a record cannot be parsed on hope. This lesson gives the
reply a contract. A schema, record@1.0.0, states the five
fields, their types, two closed enums, a summary cap, and
the rule that null is a value while absence is a breach.
Measured against it, the strongest ask this course knows how
to write — every field named, "nothing else" — files 3 of 24
records: 14 replies parse as JSON at all, and 11 of the
parses die at validation (a string where a boolean belongs, a
date in the wrong format, an invented key, a key gone
missing). The build is the machinery that closes the gap
without lying about it: a validator whose errors are located
and named, a deterministic repair layer that fixes what is
mechanical and logs every move, a loop that hands the errors
back to the model, and a constrained emitter that makes
invalid form impossible — followed by the honest residual:
under every strategy, the three records whose content the
model got wrong are filed wrong, validly. Form is solvable.
Validity is not accuracy. Everything runs offline, standard
library only, against a stand-in whose rules are printed in
full; every number is measured by the pack's own drivers.

## What was built

- `reply_lab.py` — the stand-in for this lesson: a model
  that fully intends a record and returns it in the wild's
  forms. Its rules are its docstring: the intended record is
  fixed per case (three carry named judgement errors), and
  the serialisation applies the case's printed form defects
  — fences, surrounding prose, trailing commas, Python
  reprs, string booleans, drifted enums, missing keys,
  invented keys, local date formats, an over-long summary,
  one reply that stops mid-string. It also models the two
  other roads: a cooperative re-ask (named form defects are
  dropped; content never changes) and a schema-guided
  emitter (validity by construction; the summary cap cuts
  at a word boundary; the values are the same values).
- `records.json` — the 24-case set: the Assistant's own
  inbox, each case with a gold record, the intended record,
  and its form defects. Summaries are graded on a printed
  key phrase; every other field is graded exact.
- `structured.py` — the build: the schema as data, the
  validator (located, named errors — an API, not a verdict),
  the repair layer (nine mechanical repairs, each logged;
  what no rule covers is rejected, never guessed), and
  `structured@1.0.0`, the shipped filing pipeline: ask,
  validate, repair, hand the errors back for one re-ask,
  file or reject under the case's own name.
- `run_records.py` — the measurements, in six sections: the
  wild (14 of 24 parse; the defect census); ask-only (3 of
  24 filed, field accuracy 0.867 — and two of the three are
  wrong anyway); repair (19 of 24 filed, 21 logged repairs,
  five rejections each with its reason); the loop (24 of 24
  at 29 calls, 1.21 per record, a quarter more than the ask
  batch's price); constrained (24 of 24 at one call each —
  and the same accuracy ceiling); and the shipped pipeline
  beside the ask, states itemised: 3 filed clean, 16
  repaired, 5 re-asked. Field accuracy tops out at 0.975
  and record-exact at 20 of 24 under both full strategies:
  that ceiling is the model's judgement, and no form
  machinery in this lesson moves it.

The client, providers, budgeter, tokenizer, streaming
client, prompt library, context assembler and sampling
policy are carried from 1.01–1.07 unchanged. The new
surface is the shape of what comes back.

## How to run everything

From `solution/` (no servers needed — the lab is in-process):

    python3 run_records.py            # all six sections
    python3 run_records.py repair     # or one at a time

## The exercise

In `exercise/`: file only what validates. Sixteen raw
replies arrive as data — no model to re-ask — and
`extract.py` starts as the found extractor: `json.loads`
and hope, which files six invalid records, loses seven
more, and misses all three bars. Build the deterministic
half of the pipeline — repair, validate, reject inside a
budget — until every emitted record validates, at least
13 of 16 replies file, and field accuracy reaches 0.95.
Full statement in `exercise/README.md`; the graded starting
point is `exercise/extract.py`, the harness is
`exercise/records_harness.py`, and the worked answer is in
`exercise/solution/`.

### Measurable pass condition

Run, from `exercise/`:

    python3 records_harness.py --extractor extract.py

It must report **all three bars met** and exit 0: no
invalid emissions, at least 13 of 16 records filed, field
accuracy at or above 0.95. Against the starter it misses
all three — validity (six invalid filings), yield (three
filed), accuracy (0.933). The three budgeted rejections are
the point: a missing key is not a null, a synonym is not an
enum member, and a repair you cannot log is a guess.
