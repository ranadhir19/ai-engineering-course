# Lesson 1.09 — Function Calling

Phase 1 (Inbox Assistant), Lesson 9 of 12.

## Summary

The Assistant can file a record (1.08); now it acts.
Given a task in words — find Priya's message and label
it, draft the chase for the overdue invoice — the model
stops describing the world and starts proposing
operations on it: a tool name, and the arguments as a
JSON string. This lesson builds the code those proposals
land on. The registry states the four tools that exist
(search, read a record back, apply a label, draft a
reply), each with a JSON Schema for its arguments —
1.08's contract generalised into a function's signature
— and the shipped dispatcher, agent@1.0.0, disposes of
every call in order: the tool must be in the registry,
the arguments string must parse, the arguments must
validate, and only then does anything execute. Every
failure travels back to the model as a tool result with
the validator's located, named errors, and the model
corrects exactly what was named. Measured on 24 tasks
over the Assistant's own inbox — 35 proposed calls, 14
of them formally defective on first emission (40%):
trailing commas, Python-repr strings, a number wearing
quotes, a missing argument, an invented one, a drifted
enum, an over-long draft body, one call to a tool that
does not exist, and one formally perfect call naming a
message that does not exist — the found executor
(parse-and-pray) finishes 9 tasks correctly, crashes 5,
fails 12, and silently files 3 writes in forms the
schema forbids. Fail-fast validation finishes 6 and
refuses 15. The shipped loop finishes 21, at 46 model
calls against trust's 29 — 57% more per batch, a third
less per finished task. And the honest ceiling: the same
three tasks are wrong under every strategy, because
their intended calls carry the model's judgement errors
(a label, a search's first hit, a draft's addressee),
and disposal machinery does not manufacture judgement.
The model proposes; your code disposes; neither one
grades the other's homework. Everything runs offline,
standard library only, against a stand-in whose rules
are printed in full.

## What was built

- `tools.py` — the registry: four tools with their
  JSON Schemas (types, the closed label enum, required
  arguments, length and range bounds, closed objects),
  an access level each (read / write), `validate_args`
  returning located, named errors in 1.08's style, the
  `Store` (the 1.08 inbox plus the labels and drafts a
  run creates), and the executors. A call naming a tool
  outside the registry is refused, never executed.
- `tool_lab.py` — the stand-in planner. Its rules are
  its docstring: intended plans are fixed per task
  (three carry named judgement errors); emissions apply
  the printed form defects; a correction, handed a
  located error, re-emits the intended call with the
  named defect removed (content never changes), falls
  back from an unregistered tool to the registered one
  with the same argument shape, and recovers a bad id
  by searching first and retrying with the id the
  search returns.
- `agent.py` — the disposal: `dispatch` (registry,
  parse, validate, execute — errors as results), and
  the three measured strategies: `run_trust` (the found
  executor), `run_strict` (fail-fast), `run_agent`
  (agent@1.0.0, the error-feedback loop, corrections
  capped at two per call), plus the shared grading.
- `tool_tasks.json` — the 24 tasks: instruction,
  intended turns (five tasks propose two independent
  calls in one turn — the parallel case), printed
  defects, and gold end states written before any
  dispatcher ran.
- `run_tools.py` — the measurements, in six sections:
  the wild (the first-emission census: 14 of 35 formally
  defective, plus one formally clean call wrong in the
  world); trust (9 correct, 5 crashes, 3 invalid writes
  filed silently); the shipped loop (21 correct, 15
  correction rounds, 0 invalid); fail-fast (6 correct,
  15 refused — safety bought with brittleness); parallel
  (35 calls in 30 turns, each call disposed on its own
  merits); and the summary table, with the ceiling the
  three strategies share.

The client, providers, budgeter, tokenizer, streaming
client, prompt library, context assembler, sampling
policy and structured-output machinery are carried from
1.01–1.08 unchanged. The new surface is what the model
may ask the world to do — and what the world checks
before doing it.

## How to run everything

From `solution/` (no servers needed — the lab is
in-process):

    python3 run_tools.py           # all six sections
    python3 run_tools.py agent     # or one at a time

## The exercise

In `exercise/`: dispose of sixteen tasks' proposed
calls with no model to hand errors back to. Validate
every call before executing any of them, execute the
valid, record the world's errors as results, and
refuse the rest by name — until no invalid write lands,
at least 10 of 16 tasks reach gold, and at least 0.90
of the writes on file match gold exactly. Full
statement in `exercise/README.md`; the graded starting
point is `exercise/dispatch.py` (the found dispatcher:
9 correct, precision 0.750, 2 invalid writes, 4 crashed
tasks — all three bars missed), the harness is
`exercise/tools_harness.py`, and the worked answer is
in `exercise/solution/`.

### Measurable pass condition

Run, from `exercise/`:

    python3 tools_harness.py --dispatcher dispatch.py

It must report **all three bars met** and exit 0: zero
invalid executions and zero crashes, at least 10 of 16
tasks at gold, write precision at or above 0.90. The
worked solution meets all three (11 correct, 0.917,
nothing invalid, nothing crashed); its seven refused
calls — an unparseable get, a drifted enum, an
unregistered tool, a redundant call's defective twin,
an over-long body, a mistyped search, a missing
argument — are the point: the
contract's answer to an unmechanical defect is
refusal, and the completion budget is set so honesty
stays affordable.
