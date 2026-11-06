# Lesson 1.10 — Validation at the Boundary

Phase 1 (Inbox Assistant), Lesson 10 of 12.

## Summary

Two crossings are guarded. The model's reply is filed
under a contract (1.08); the model's proposed calls are
disposed before they execute (1.09). But a system has a
whole perimeter, and everything else has been crossing
unchecked: the user's request on its way in, the tool's
result on its way back into the conversation, and the
Assistant's own records on their way back out of the
store — written months ago, under older versions of the
contract, by writers nobody would vouch for now. This
lesson builds the one pattern that guards all of it:
a boundary gate that asks every crossing the same
question — what are you, and may you pass? — and
answers with one of four dispositions, always with
located, named reasons: **admit** what satisfies its
contract, **repair** what closed mechanical rules
(logged) or a printed versioned migration can settle,
**quarantine** what is interpretable but not
admissible until a decision settles it, and **reject**
what cannot be interpreted at all. Measured on 31
authored crossings — 10 requests, 8 tool results, 13
records read back from a store snapshot: pass-through
(no boundary) admits all 31, 18 of them in forms that
fail their own contracts, and leaves a store where 6
of 12 records fail the record contract and a duplicate
line has silently overwritten a true record.
Reject-only validation is perfectly safe and loses 7
legitimate crossings — every drifted record, padded
request and extra key refused with the bit-rotted.
The shipped gate, boundary@1.0.0, admits 19 (11 as
they stand, 8 repaired, every repair logged), holds 6
in quarantine with reasons, rejects 6 by name, loses
nothing legitimate and admits nothing invalid — for
about two milliseconds of local CPU per corpus and
zero model calls. And the ceiling, planted in the
open: two crossings are formally perfect and wrong —
a request naming the wrong message, and 1.09's
judgement error read back from rest, valid in every
field. Every strategy admits both. Validation
certifies form and provenance; it has never certified
truth.

## What was built

- `boundary.py` — the gate, boundary@1.0.0: the three
  contracts as data (request@1.0.0; result@1.0.0 per
  tool, with the embedded record checked against
  record@1.0.0; records at rest under their version
  stamps), validators returning located, named errors
  in 1.08's style, the closed repair set (control
  characters, whitespace canonicalisation, undeclared
  keys, enum case-folds, instruction-shaped data
  quoted as data), the printed migration tables
  (record@0.9.0 and search@0.9.0), `inspect()` giving
  each crossing its disposition, `inspect_call()` —
  the same gate at 1.09's surface — and the two
  comparison strategies (pass-through, reject-only).
- `crossing_lab.py` — the specimen rules, printed in
  full: how each wild crossing in the corpus was
  produced from its intended form.
- `crossings.json` — the 31 crossings: intended form,
  wild form, defect tags, and the gold disposition,
  written before any gate ran.
- `store_snapshot.jsonl` — the store as read back:
  thirteen lines, three of them written by
  record@0.9.0, one bit-rotted, one a second claim on
  an id already filed.
- `run_boundary.py` — the measurements, in six
  sections: the wild (the census: 22 of 31 crossings
  carry a defect), pass-through (31 admitted, 18
  invalid, a poisoned store, zero reasons logged),
  reject-only (13 admitted, 0 invalid, 7 legitimate
  lost), the gate (11 admit / 8 repair / 6 quarantine
  / 6 reject, agreeing with the gold dispositions on
  all 31), cost (≈61 µs per crossing, 0 model calls),
  and the summary — the three strategies on one table,
  the unification (the gate at 1.09's surface agrees
  with the dispatcher on all 35 first emissions), and
  the ceiling both wrong crossings set.

The client, providers, budgeter, tokenizer, streaming
client, prompt library, context assembler, sampling
policy, structured-output machinery, tool registry and
dispatcher are carried from 1.01–1.09 unchanged. The
new surface is the perimeter itself — every way
anything enters, returns, or is read back.

## How to run everything

From `solution/` (no servers needed — the lab is
in-process):

    python3 run_boundary.py            # all six sections
    python3 run_boundary.py boundary   # or one at a time

## The exercise

In `exercise/`: gate sixteen crossings with no sender
to correct them and no model to re-ask. Give every
crossing a named disposition with its reason, admit
nothing invalid, lose nothing legitimate, and hold
what only a decision can settle — until no invalid
form is admitted, at least 7 of the 8 legitimate
crossings are in in valid form, and all sixteen are
accounted for with at least 3 held in quarantine.
Full statement in `exercise/README.md`; the graded
starting point is `exercise/admit.py` (the found
pass-through: 12 invalid admitted, 4 of 8 legitimate
in valid form, nothing accounted for — all three bars
missed), the harness is `exercise/boundary_harness.py`,
and the worked answer is in `exercise/solution/`.

### Measurable pass condition

Run, from `exercise/`:

    python3 boundary_harness.py --gate admit.py

It must report **all three bars met** and exit 0: zero
invalid admissions, at least 7 of 8 legitimate
crossings admitted in valid form, and every crossing
accounted for with at least 3 held in quarantine. The
worked solution meets all three (0 invalid, 8 of 8,
4 held, every disposition as gold); its four held
crossings — an over-cap request, a result under the
wrong contract, a priority no version ever allowed, a
summary an old writer ran past its cap — are the
point: the gate's answer to what it may not settle is
a named hold, and the yield budget is set so honesty
stays affordable.
