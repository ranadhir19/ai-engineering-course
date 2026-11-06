# Lesson 1.07 — Temperature & Sampling

Phase 1 (Inbox Assistant), Lesson 7 of 12.

## Summary

Every stand-in in this course has been deterministic — same
input in, same answer out — and 1.06 closed by naming that as a
choice. A production model is not like that: it holds a
distribution over what it might say and samples from it under
controls the caller sets. Those controls — temperature,
candidate filters, number of draws — are almost never set on
purpose; the provider default (temperature 1, no filters, one
draw) is inherited by accident and then blamed on the model.
This lesson builds a sampling laboratory on the Assistant's own
three task families and measures what the dials do. Triage
extraction and rubric grading sell the same answer every time:
at the inherited default the filer files 0.680 of its cases
correctly and the grader matches its own gold 0.584 of the
time, while greedy decoding — temperature 0 — files 0.917 and
grades 0.900 exact with a mean absolute error of 0.10.
Brainstorming sells the opposite product: greedy repeats one
subject line forever (1.0 distinct in 300 draws), temperature
restores the variety (11.7 distinct), and a top-p cut at 0.9
keeps 8.7 lines in rotation while the off-brief tail line is
never drawn at all. Majority voting is measured against the
greedy line and priced: it buys back most of what temperature
spends, and its one apparent win is a 40% rescue rate on a
nearly-tied case — a slower coin, at up to nine times the
price. The build is the decision itself: `sampling@1.0.0`, one
defended setting per task family. Everything runs offline,
standard library only, against a seeded stand-in whose rules
are printed in full; every number is measured by the pack's
own drivers.

## What was built

- `sampling_lab.py` — the stand-in sampler for this lesson.
  The earlier stand-ins answered deterministically; they have
  nothing to say about sampling, so the lab is a small
  documented simulator of the sampling step itself: per-case
  candidate logits (the model's judgement, fixed before the
  dials), the textbook softmax over logit / T with temperature
  0 as greedy, top-k and top-p truncation with renormalisation,
  and seeded draws under a printed seed formula, so every
  measurement reproduces exactly. Its rules are its docstring.
- `tasks.json` — the three suites. Extraction: 12 inbox cases
  over 1.05's label set, each with candidate logits and a gold
  — including ex-07, a follow-up question the distribution
  misfiles outright, kept in the set because no sampling
  setting fixes a wrong argmax and the lesson says so.
  Grading: 10 drafted replies scored 1–5 against the rubric,
  including gr-09, the polished draft whose distribution
  prefers the wrong score. Brainstorming: 3 subject-line
  prompts with 12 candidates each and one off-brief line per
  prompt (the spam line, the wrong-register line, the wrong
  meeting) sitting in the tail where heat can reach it.
- `sampling.py` — the build: `sampling@1.0.0`, the defended
  settings (extraction and grading at temperature 0;
  brainstorming at temperature 1.0 with top-p 0.9), plus the
  measurement machinery — per-draw and replica-averaged
  filed-answer metrics for accuracy, exact match, MAE,
  agreement, diversity, concentration and tail draws.
- `run_sampling.py` — the measurements, in five sections: the
  softmax of one real distribution at five temperatures with
  its entropy (0.00 bits at greedy to 1.68 bits at T = 2);
  the sweep across all three families (extraction per-draw
  accuracy 0.917 greedy, 0.700 at the default, 0.558 at 1.5;
  grading exact 0.900 down to 0.467; brainstorming distinct
  1.0 up to 12.0 with the off-brief tail growing 0.0 → 2.3
  per 300); the filters at temperature 1 (top-p keeps the
  variety and cuts the tail; top-k 2 strangles it to 2.0
  distinct); majority voting at 0.7 (0.817 → 0.913 → 0.950
  filed accuracy at 1, 5, 9 votes, priced per answer on
  atlas); and the shipped policy beside the inherited
  default, at the same price per draw — the default spends
  accuracy, not money.

The client, providers, budgeter, tokenizer, streaming client,
prompt library and context assembler are carried from
1.01–1.06 unchanged. The new surface is the dial.

## How to run everything

From `solution/` (no servers needed — the lab is in-process):

    python3 run_sampling.py            # all five sections
    python3 run_sampling.py sweep      # or one at a time

## The exercise

In `exercise/`: set the dials. `SETTINGS` in `sampling.py`
starts as the inherited default — one global temperature 1.0,
no filters, one draw, for all three families — and fails
three of the harness's six bars. Choose a setting per task
until every bar is met. Full statement in `exercise/README.md`;
the graded starting point is `exercise/sampling.py`, the
harness is `exercise/sampling_harness.py`, the suites are
shared with the lesson (`exercise/tasks.json`, identical to
`solution/tasks.json`), and the worked answer is in
`exercise/solution/`.

### Measurable pass condition

Run, from `exercise/`:

    python3 sampling_harness.py --settings sampling.py

It must report **all six bars met** and exit 0: extraction
filed accuracy at or above 0.90, grading exact at or above
0.70 with MAE at or below 0.35, brainstorming distinct at or
above 8.0 of 12 with top-1 share at or below 0.45 and
off-brief at or below 3 per 300 draws. Against the starter it
misses three bars — the honest baseline the lesson starts
from. No single global setting passes: that is the exercise.
