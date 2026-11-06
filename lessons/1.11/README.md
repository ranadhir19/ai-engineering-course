# Lesson 1.11 — Prompt Injection & AI Security Basics

Phase 1 (Inbox Assistant), Lesson 11 of 12.

## Summary

1.10's boundary gate certifies the FORM of everything that
crosses. Every payload in this lesson is formally perfect —
in-contract, well-typed, plausible — and aimed. The question
changes from *is it well-formed?* to *who wrote it, and may
it instruct?* The asset under attack is not the data; it is
the Assistant's tool authority: the right to label the whole
inbox and to write drafts in the user's name. An injection is
any content that spends that authority without the user's
instruction. Measured on 30 authored episodes — 24 attacks in
nine classes (plain override, tool-call hijack, exfiltration
by draft, paraphrase, principal mimicry, encoded payloads,
payloads pasted in by the user, edited delegated documents,
and one purely semantic plant) plus 6 benign controls,
including a genuine delegation and a record whose summary
legitimately quotes an instruction as a joke. With no defence
(agent@1.0.0 reading everything as instruction), all 24
payloads execute. Channel discipline alone — only the user's
turn instructs, content is data — stops 13, including every
paraphrase: wording novelty is irrelevant when the channel
decides. The five surviving channels are the ones discipline
cannot close: mimicry (content framed as a principal),
encoded payloads (the model decodes, then obeys), pastes
(carried in on the trusted channel, by the user), delegated
sources (authorised, then edited), and semantic content (a
claim, not a call). The shipped stack, security@1.0.0, adds
1.10's pattern at two new points: a deterministic boundary
SCREEN over non-principal content (holds on form:
impersonation markers, instructions addressed to the
assistant on data surfaces, encoded runs), and an ACTION
GATE at dispatch (a call must stay inside the task's
declared working set — G1–G4). Result: breaches 24 → 11 → 3,
at a measured ≈22 µs per episode and zero model calls — and
a priced availability cost: 14 of 30 contents held for a
principal's decision, one of them benign (the quoted joke:
a screen that can hold an order cannot decline its identical
quotation — the pre-registered gold predicted 7 holds, the
screen holds 14, and the correction is printed in the run,
section 5, not buried). The three residuals are written into
the shipped statement, not footnoted: two delegated
documents whose authorship failed while their scope held
(delegation transfers trust; the gate checks scope, not
authorship), and one draft that carries a planted claim out
under the user's own authorised instruction (the gate checks
calls, not claims). No defence theatre: what this stack does
not stop is part of its spec.

## What was built

- `security.py` — the defence, security@1.0.0: the boundary
  screen (`PATTERNS` as data — system-mimicry, policy-claim,
  instruction-to-assistant, override-shape, mass-action-shape,
  encoded-run, spaced-run — each hold naming the pattern that
  fired), the surfaces the screen guards (paste and delegation
  deliberately excluded, both gaps measured), the action gate
  (G1 target in the working set, G2 a draft's quoted records
  in the working set, G3 no wildcard targets, G4 refuse by
  name, never rewrite), and the three measured configurations
  as data (`CONFIGS`).
- `attack_lab.py` — the episode runner: the "model" is a
  printed rule set (R1–R6), not a language model — only the
  user's turn instructs; trust follows any instruction found
  anywhere; discipline's five exception channels are named in
  `ELEVATED`; outcomes are graded as clean / ignored / held /
  refused / breach, with task_done and breach kept as separate
  facts throughout.
- `episodes.json` — the 30 episodes: user instruction, task
  working set, the content as it arrives, the payload's
  intended call and effect stated in the data, and gold
  outcomes authored with the fixtures, before the defence
  code (the `about` note is the pre-registration; it also
  records the one correction — seven extra screen holds —
  with the safety half of the key unmoved: 3 breaches
  predicted, 3 measured, the same three episodes).
- `run_security.py` — the measurements, in six sections:
  the wild (the census: the asset is tool authority, every
  payload formally perfect), trust (24 of 24 execute),
  delimiters (11 survive; the five open channels), the
  shipped stack (every hold and refusal named by pattern or
  rule; 30/30 agreement with the corrected gold), the table
  and the cost (breaches by class across the three
  configurations; ≈22 µs per episode, 0 model calls, 14
  holds owed; the gold correction printed), and the ceiling
  with the shipped statement (the three residuals read back
  by name).

Everything from 1.01–1.10 is carried unchanged — client,
providers, budgeter, tokenizer, streaming client, prompt
library, context assembler, sampling policy, structured-output
machinery, tool registry, dispatcher, boundary gate. The new
question sits on top of the whole perimeter: provenance.

## How to run everything

From `solution/` (no servers needed — the lab is in-process):

    python3 run_security.py

## The exercise

In `exercise/`: sixteen fresh episodes, one found defence —
channel discipline alone, `exercise/policy.py` — which
executes five payload calls through the channels discipline
cannot close and accounts for almost nothing (2 of 3 bars
missed). Rebuild it to meet all three bars: zero payload
calls executed outside the named residual class, at least 8
of 16 tasks completed, and every episode accounted for with
its reason — residuals stated, never claimed as stops. Full
statement in `exercise/README.md`; harness is
`exercise/security_harness.py`; worked answer in
`exercise/solution/policy.py`.

### Measurable pass condition

Run, from `exercise/`:

    python3 security_harness.py

It must report **all three bars met** and exit 0: 0 executed
payload calls outside the residuals, at least 8 of 16 tasks
completed, 16 of 16 episodes named with at least 10 held or
refused across the run and both residuals stated. The worked
solution meets all three (0 executed, 8 completed, 16 named,
10 held/refused, residuals stated, 16 of 16 outcomes as
gold); the found defence misses safety (5 executed) and
accounting (6 named, residuals hidden) while passing yield
16 of 16 — availability was never its problem.
