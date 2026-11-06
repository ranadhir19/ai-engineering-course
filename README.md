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
- **1.02 Models & Providers** — one interface over three providers,
  switchable by config, with cost and latency measured per call.
- **1.03 Tokens & Context Windows** — what a token is, why windows
  fill, and a token counter and context budgeter inside the client.
- **1.04 APIs, SDKs & Streaming** — when the SDK helps, when it hides
  the thing that breaks, and streaming with a clean abort.
- **1.05 Prompt Engineering** — instructions, examples and structure
  as programming; a versioned prompt-template library.
- **1.06 Context Engineering** — the context window as a workspace
  you design: what earns a place in it, and what each inclusion costs.
- **1.07 Temperature & Sampling** — what sampling does to a
  distribution, measured on the Assistant's own tasks.
- **1.08 Structured Outputs** — schemas as contracts, with
  schema-validated extraction and a repair loop.
- **1.09 Function Calling** — the model proposes, the code disposes:
  real tools with full validation.
- **1.10 Validation at the Boundary** — input sanitisation and output
  checking as middleware around every model call.
- **1.11 Prompt Injection & AI Security Basics** — the attack
  classes, stated honestly, with tripwires on the middleware.
- **1.12 Measure Everything: Cost, Latency, Testing & Logging** —
  per-call instrumentation, a golden-set test runner, structured logs.
- **Phase 1 Capstone — The Inbox Assistant, Finished** — the thread
  application completed to a stated, checkable standard.

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
lesson folder's structure, and runs the lesson exercise harnesses
(1.01 failure harness, 1.02 routing harness, 1.03 budget harness)
against the exercise solutions.

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
