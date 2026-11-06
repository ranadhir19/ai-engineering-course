# Exercise 1.05 — Fix the failing prompt

The starter's `prompts.py` in this folder contains the triage
prompt exactly as it was found in the wild: one cheerful sentence
and the raw email, unlabelled and undelimited. It is not a straw
man. Against the 20-case test set it names the right label in 12
cases — and scores **0 of 20**, because the Assistant's downstream
code does not read prose: it parses, strictly, and a sentence that
mentions a label is not a label. What is broken is not the model's
judgement. It is the prompt's engineering. That is your exercise.

## The task

Rebuild `build_messages(email_text)` in `prompts.py` until the
harness reports **18 of 20 or better**, changing only the prompt —
the model (the lesson's stand-in, `../solution/prompt_lab.py`,
whose rules are printed in its docstring) and the test set are not
yours to edit. Then document the failures that remain in a short
`failures.md` beside your prompt: which cases, what the prompt
said, and your best account of why.

The failure families are named in the lesson, and the test set is
built so each family is visible in the report:

- **format** — completions a parser cannot use (prose, hedges,
  decorations) fail every case they touch, however right they are;
- **drift** — a label set the prompt never closed gets answered in
  the model's own synonyms ("urgent", "read-later", "bin");
- **injection** — an instruction written *inside* an email is an
  instruction the model will follow, unless the prompt gives it a
  reason not to;
- **convention** — some labels are house conventions, not
  deductions: a question the email itself answers, a receipt
  confirmation on an announcement, a question riding with an
  undated ask. Conventions are taught by examples or not at all.

## The rules of the road

- Standard library only; the stand-in model and the label set come
  from `../solution/` (already importable from the harness).
- `build_messages` returns the message list; it must work for any
  email text, not the twenty it is graded on — a prompt that
  memorises the test set has learned the wrong lesson, and the
  conventions it needs are general ones.
- Every change should be one change: when the score moves, you
  should be able to say which change moved it, and which cases it
  fixed. That is the difference between engineering a prompt and
  negotiating with one.

## How you are graded

    python3 prompt_harness.py --prompts prompts.py   # grade YOUR prompt
    python3 prompt_harness.py                        # grade the worked solution

The harness runs all 20 cases in `cases.json` through the stand-in
and grades strictly: the completion, stripped, must be exactly the
gold label. Exit 0 at 18/20 or better.

Run it against the starter first to see the honest baseline — 0 of
20 strict, 12 of 20 by mention (the 12 is in the lesson's driver,
`../solution/run_prompts.py`; the harness itself reports the
strict count and what each failing completion actually said).

The worked answer lives in `solution/prompts.py` in this folder —
it delegates to the lesson's versioned template library at its
current version and scores 20/20. Try the exercise before you read
it; then be able to explain, in one sentence each, what the
instructions bought, what the structure bought, and what only the
examples could buy.
