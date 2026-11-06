# Exercise 1.09 — Dispose of the calls yourself

The lesson's loop hands the validator's errors back to a
live model, and the model corrects itself. This exercise
takes the model away. Sixteen tasks arrive with their
proposed calls as **data** — wire dicts emitted by the
lesson's own lab, defects included — and there is nobody
to re-ask. What you build is the disposal half of the
pipeline, standing alone:

- **validate every call before executing any of them** —
  the registry (is this tool real?), the parse (is the
  arguments string JSON?), the schema (do the arguments
  satisfy the signature?);
- **execute the valid calls**, in order, recording an
  execution error (a message id the world does not have)
  as that call's result instead of dying on it;
- **refuse the rest, by name**, with the reason attached.

## The bars

`tools_harness.py` grades `dispatch.py` (interface:
`run_task(calls, store)` returns a log with `results`
and `refused`) against three bars, stated before any
code:

1. **Safety — absolute.** Zero invalid executions and
   zero crashed tasks. An invalid execution is a write
   sitting in the store in a form the tool's schema
   forbids; downstream reads the store and trusts it.
2. **Completion — at least 10 of 16** tasks reach their
   gold end state exactly (labels exact, drafts byte
   for byte, gold facts in the returned results). Six
   tasks cannot be completed honestly; refusal is
   legitimate and priced out of this budget.
3. **Precision — at least 0.90** of the writes on file
   match gold exactly. One planted judgement error
   (ex-12) caps every dispatcher below 1.0; the bar
   sits under the ceiling.

## The traps, named in advance

- **Coerce everything.** Rewrite a drifted enum ("info"
  must mean fyi), invent a missing argument, substitute
  the tool you have for the tool that was called — and
  completion climbs while safety's spirit dies: your
  code is now making the model's judgements, silently,
  forever. The harness catches the two that land in
  forbidden forms; the habit is the real failure.
- **Refuse everything.** Safety is perfect and nothing
  ever happens: a dispatcher that files nothing is a
  very safe outage. Completion exists to bury it.
- **Execute first, validate later.** The paired calls
  in ex-04 and ex-14 are independent, but a task is
  disposed as a whole: one invalid sibling executed
  before its check is a write you cannot take back.
- **Let the world crash you.** ex-09's first call names
  a message that does not exist. That is a result, not
  an exception: the label call behind it is valid and
  still owed.

## Run it

    python3 tools_harness.py                       # the worked solution
    python3 tools_harness.py --dispatcher dispatch.py   # your attempt

The starting point, `dispatch.py`, is the found
dispatcher — parse-and-pray: it drops a call
silently, crashes four tasks, lands two invalid writes,
and misses all three bars (9 correct, precision 0.750).
The worked solution in `solution/` validates against
the shipped registry, executes the valid, refuses
seven calls by name, and meets all three bars: 11 correct,
precision 0.917, nothing invalid, nothing crashed. The
one write it gets wrong is ex-12 — the planted
judgement, filed faithfully, as the lesson predicts.
