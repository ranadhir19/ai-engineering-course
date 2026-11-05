# AI Engineering — The Complete Course

Companion code for the course *AI Engineering — The Complete Course*,
from The Architect's AI Workshop channel.

Every lesson ships runnable code that needs nothing but Python 3 and its
standard library. No installs, no API keys, no network: each lesson
pairs a small client you build yourself with a local mock server, so
the HTTP on the wire is real and inspectable while the "model" is
deterministic and offline.

## The course map

The course is one long thread in three phases. Each phase builds a
system, and the next phase grows out of the one before it.

### Phase 1 — Inbox Assistant

Build a client that talks to a model endpoint over HTTP, then harden it
until it survives everything the wire can do to it. The running thread
system is a personal **Inbox Assistant** that answers questions about a
small inbox of emails.

### Phase 2 — Knowledge Service

Give the assistant real material to answer from: documents, chunking,
embeddings, ranking and a small HTTP service of its own. The thread
system becomes a **Knowledge Service** that other programs can call.

### Phase 3 — Agent Platform

Let the system act: tools, planning loops, memory, evaluation and
guardrails, assembled into an **Agent Platform** that runs the Inbox
Assistant and the Knowledge Service as tools of its own.

## Phase 1 lessons

- **1.01 The Toolkit: Python, JSON & HTTP** — a chat client and a mock
  model server, built from the standard library alone.
- **1.02 Prompts, Messages and Roles** — system, user and assistant
  turns, and what each one is actually for.
- **1.03 Tokens, Context and Cost** — counting what you send, budgeting
  a context window, reading usage numbers honestly.
- **1.04 Structured Output** — asking for JSON, validating what comes
  back, and repairing what does not parse.
- **1.05 Errors, Retries and Timeouts** — a failure taxonomy for model
  calls, and backoff that respects the server.
- **1.06 Conversation Memory** — carrying state across turns without
  losing the thread or the budget.
- **1.07 Tool Calling Basics** — letting the model ask your code to do
  things, safely.
- **1.08 Retrieval over Your Inbox** — keyword search first, then
  ranking, over the same three-email inbox grown up.
- **1.09 Embeddings and Similarity** — vectors from scratch, and what
  they buy over keywords.
- **1.10 Evaluation Harnesses** — measuring an assistant with tests
  instead of vibes.
- **1.11 Keys, Privacy and Local-First Design** — secrets in the
  environment, redaction in logs, and what never leaves the machine.
- **1.12 The Inbox Assistant, Assembled** — every piece from the phase
  in one small, honest program.
- **Phase 1 Capstone — Inbox Assistant** — build the complete assistant
  against a fresh inbox and a fresh failure harness, unaided.

Lessons for Phases 2 and 3 are added to this repository as the course
reaches them.

## How a lesson folder is organised

Each lesson lives under `lessons/` in a folder named by its number,
for example `lessons/1.01/`, and contains:

- `README.md` — what the lesson builds, the exercise statement, and
  the measurable condition that says you passed it.
- `starter/` — the skeleton you start from: same public interface as
  the solution, with the interesting bodies replaced by guided TODO
  steps. It imports and runs; it just does not do the work yet.
- `solution/` — the complete, worked version from the video.
- `exercise/` — the follow-on task that hardens or extends the
  solution, with its own harness. The exercise's own `solution/`
  subfolder holds the worked answer to the exercise.

## How to run an exercise harness

From the repository root:

    python3 validate.py

That compiles every Python file in the repository, checks each
lesson folder's structure, and runs the lesson 1.01 failure harness
against the exercise solution client.

To run one harness directly, from its lesson's exercise folder:

    cd lessons/1.01/exercise
    python3 failure_harness.py

It prints one PASS or FAIL line per scenario and exits non-zero if
anything fails. Point it at another client to test that client instead,
for example the unhardened starting client in the same folder:

    python3 failure_harness.py --client inbox_client.py

## Ground rules for all the code here

- Python standard library only, everywhere. If a lesson needs a new
  idea, it builds the idea; it does not install it.
- Deterministic and offline: mock servers, fixed data, no live APIs.
- Errors are part of the interface. Every client in this repository
  raises typed exceptions, never bare strings or silent `None`.
