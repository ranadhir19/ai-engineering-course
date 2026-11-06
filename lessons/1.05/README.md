# Lesson 1.05 — Prompt Engineering

Phase 1 (Inbox Assistant), Lesson 5 of 12.

## Summary

Every lesson so far engineered everything around the prompt — the
client, the providers, the budget, the stream — and left the prompt
itself as a string somebody typed once. This lesson turns the same
discipline on the words upstream. A prompt is treated as what it
measurably is: a function with a signature (named inputs), a
contract (a closed label set, an exact answer shape), and failure
modes that can be enumerated, reproduced, and fixed one at a time.
The Assistant gains a job — triage, one of four labels per email —
and a failing prompt to fix against a 20-case test set. The fix is
measured at every step: instructions take the strict score from 0
to 15 of 20, structure to 17, examples to 19, and the last case
falls to a one-example patch shipped the way code fixes ship —
as a new version of a prompt-template library, with a regression
run and a changelog. Everything runs offline, standard library
only, against a deterministic stand-in whose rules are printed in
full; every number is measured by the pack's own drivers.

## What was built

- `prompt_lab.py` — the stand-in model for this lesson. The
  1.02–1.04 providers answer questions; they have nothing to say
  about prompts, so the lab is a small documented simulator of how
  a production model treats one: it classifies by features, answers
  in prose unless given a shape, drifts to its own synonyms when
  the label set is left open, obeys instructions written inside
  the email unless the prompt delimits the email *and* says the
  delimited text is data, and applies house conventions only when
  a worked example demonstrates them. Its rules are its docstring;
  nothing about it is hidden, which is what makes scores against
  it meaningful.
- `cases.json` — the 20-case test set: seven plain cases, three
  label-drift cases, two in-email injections, three house
  conventions, five controls that must not regress. Gold labels
  follow the conventions the set itself states.
- `prompts.py` — the build: a versioned prompt-template library
  for the Assistant's tasks. A template is a name, a semver
  version, system and user texts with named `{placeholders}`, and
  a changelog. Rendering is checked — a missing input raises
  `MissingInputError` before any model call exists. The triage
  history is the lesson: 0.1.0 the failing prompt (0/20 strict,
  12/20 by mention), 0.2.0 instructions (15/20), 0.3.0 structure
  (17/20), 1.0.0 examples (19/20, case 15 documented), 1.1.0 the
  one-example patch (20/20, zero regressions). The 1.02/1.03
  workload prompts (`summarise`, `answer`) are packaged unchanged
  as the library's other tenants.
- `triage.py` — the integration: render the template, call the
  backend, parse strictly. A completion that is not exactly one
  label raises `TriageParseError`; the Assistant's own inbox —
  the three emails every lesson since 1.01 has answered questions
  about — is filed by triage@1.1.0 as three announcements, three
  fyi.
- `run_prompts.py` — the measurements, in five sections: the
  ladder (one change at a time, with the cases each change fixed),
  the library (the 1.0.0 → 1.1.0 patch, its regression run, the
  changelog), the price of accuracy (the 20-case suite costs
  $0.000873 at 0.2.0 and $0.002905 at 1.1.0 on atlas prices — the
  prompt is the biggest input the Assistant sends: one triage call
  at 1.1.0 is 179 words by the servers' meter, 591 tokens by
  1.03's BPE counter), the render guard, and the thread.

The client, providers, budgeter, tokenizer and streaming client
are carried from 1.01–1.04 unchanged. The new surface is the words.

## How to run everything

From `solution/` (no servers needed — the lab is in-process):

    python3 run_prompts.py            # all five sections
    python3 run_prompts.py ladder     # or one at a time

## The exercise

In `exercise/`: fix the failing prompt. `build_messages` in
`prompts.py` starts as the prompt as found; rebuild it until the
20-case harness reports 18 of 20 or better, and document the
failures that remain. Full statement in `exercise/README.md`; the
graded starting point is `exercise/prompts.py`, the harness is
`exercise/prompt_harness.py`, and the worked answer is in
`exercise/solution/`.

### Measurable pass condition

Run, from `exercise/`:

    python3 prompt_harness.py --prompts prompts.py

It must report **18 of 20 or better** and exit 0, with the
remaining failures documented in a `failures.md` beside the
prompt. Against the starter it reports 0 of 20: the model names
the right label in 12 cases, and a strict parser can use none of
them — the honest baseline the lesson starts from.
