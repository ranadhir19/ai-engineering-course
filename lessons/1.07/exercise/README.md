# Exercise 1.07 — Set the dials

The starter's `sampling.py` in this folder contains the
Assistant's sampling settings exactly as they were found in
the wild: the provider default, inherited without a decision.
One global temperature of 1.0, no candidate filters, one draw
— for a triage filer, a rubric grader and a brainstorming
tool alike, as if variance meant the same thing to all three.
It does not. The filer files 0.680 of its cases correctly at
that default; the grader repeats its own gold 0.584 of the
time. What is broken is not the model. It is the settings.
That is your exercise.

## The task

Choose a setting per task — `temperature`, `top_k`, `top_p`,
`vote_k` — in `SETTINGS` in `sampling.py`, until the harness
reports **all six bars met**, changing only the settings: the
lab (the lesson's stand-in, `../solution/sampling_lab.py`,
whose rules are printed in its docstring), the suites
(`tasks.json`) and the measurement code are not yours to
edit. The suites are the Assistant's own: 12 extraction cases
with gold labels, 10 grading cases with gold scores, 3
brainstorming prompts with 12 candidate lines each and one
off-brief line per prompt.

The six bars, stated in the lesson before any code:

- **extraction** — filed-answer accuracy at or above 0.90.
  Triage files legal and financial mail; a filer that is
  right seven times in ten is not a filer.
- **grading** — filed exact match at or above 0.70 **and**
  mean absolute error at or below 0.35. A grade is an audit
  record: the same grade when the run repeats, and when it
  misses, it misses by a little.
- **brainstorming** — distinct lines at or above 8.0 of 12 in
  300 draws, the top line's share at or below 0.45, and
  off-brief draws at or below 3 per 300. Variety is the
  product — but one line must not swallow the send, and the
  off-brief tail is a defect, not spice.

Filed answers are graded as the majority of `vote_k` draws,
averaged over 25 replicas — a single replica's vote is itself
a draw, and the harness does not grade luck.

## The trap, named in advance

No single global setting passes, and both obvious ones fail
instructively. Set everything to 0 and extraction and
grading pass while brainstorming collapses to one repeated
line. Leave everything at 1.0 and brainstorming passes while
the filer and the grader fail. Crank everything to 1.5 and
even brainstorming's tail turns against you. The way through
is per-task settings, each defended by its family's own
measurement — which is the entire content of the lesson,
now in your hands.

Two honest warnings from the measurements. First, voting is
not a loophole around thinking: a majority of draws from a
distribution that prefers the wrong answer is a wrong answer
with a quorum, and case ex-07 is built to show you exactly
that — its rescue rate, not its score, is the number to
report. Second, if a bar seems to pass by a hair at some
temperature, check it at the replica level before you ship
it: the harness averages 25 replicas precisely so that a
lucky seed cannot impersonate a setting.

## The rules of the road

- Standard library only; the lab, the suites and the
  measurement code come from `../solution/` (already
  importable from the harness).
- `SETTINGS` must carry one setting per family —
  `extraction`, `grading`, `brainstorming` — each a dict with
  `temperature`, `top_k`, `top_p`, `vote_k`. That dict is the
  deliverable; everything else is measurement.
- Defend each setting in one sentence: what the family's
  product is (the same answer, or variety), what the dial
  buys there, and what it costs. A setting you cannot defend
  in one sentence is a default with extra steps.

## How you are graded

    python3 sampling_harness.py --settings sampling.py   # grade YOUR settings
    python3 sampling_harness.py                          # grade the worked solution

The harness runs all three suites through the lab at your
settings and applies the six bars. Exit 0 only when every
bar is met.

Run it against the starter first to see the honest baseline —
three bars missed, each failure a family the default was
never chosen for. The worked answer lives in
`solution/sampling.py` in this folder: it delegates to the
lesson's shipped policy and passes all six. Try the exercise
before you read it; then be able to explain, in one sentence
each, what determinism bought the filer, what it bought the
grader, what the nucleus bought the brainstorm, and what
voting would have cost to buy the same things worse.
