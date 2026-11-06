# Lesson 1.02 — Models & Providers

Phase 1 (Inbox Assistant), Lesson 2 of 12.

## Summary

Lesson 1.01 built one client for one endpoint. Real systems choose:
the same question can be answered by a small cheap model, a balanced
model, or a frontier model, and the three differ in context window,
price, latency and terms. This lesson builds **one interface over
three providers, switchable by configuration alone**, wires it into
the hardened 1.01 client, and measures what each choice costs — in
tokens, dollars and seconds — on a real workload. The providers are
local stand-ins with published price tables, context limits and
simulated latency, so every number in the lesson is measured, not
asserted, and everything runs offline with the standard library only.

## What was built

- `mock_provider_server.py` — one process emulates one provider
  (`--profile sprout|atlas|oracle`, ports 8771/8772/8773). Profiles
  differ in model name, context limit (600 / 4,000 / 20,000 tokens),
  simulated latency (0.30 s / 0.15 s / 0.60 s) and prices per million
  tokens (in/out: $0.15/$0.30, $0.80/$1.60, $5.00/$15.00). A prompt
  over the context limit is rejected with HTTP 400 and error code
  `context_length_exceeded` — never silently truncated. Answers are
  extractive over the same three-email inbox as 1.01; a user message
  starting with "summarise" gets a digest of all three.
- `inbox_client.py` — the hardened 1.01 client, unchanged, plus the
  `PROVIDERS` table (everything that differs between providers is
  data: base URL, model, key environment variable, prices, context
  limit) and `ProviderClient`, which binds the client to one row:
  no model argument, per-call timing, dollar cost from the usage
  counts, and two re-named failures — `ContextTooLargeError` and
  `ProviderUnavailableError`. There is no silent fallback anywhere:
  choosing a provider is the caller's decision, in the open.
- `compare_providers.py` — one question through all three providers,
  with the three receipts side by side, then the honest failure:
  the ~750-token brief sent to the 600-token provider.
- `ask_via.py` — the same question with the provider chosen by the
  `INBOX_PROVIDER` environment variable. No code changes.
- `route_workload.py` + `workload.py` + `router.py` — a six-task
  workload (short questions, a document question, a summary) run two
  ways: all-frontier, and routed by the lesson's rule. Measured on
  this pack: routed **$0.0055069** vs all-oracle **$0.0126100** —
  43.7% of the cost, and faster (1.87 s vs 3.63 s).

## How to run everything

From `solution/` (drivers start the three servers themselves):

    python3 compare_providers.py
    python3 route_workload.py

To run `ask_via.py` standalone, start the servers first, one per
terminal, then:

    INBOX_PROVIDER=oracle python3 ask_via.py

The starter folder is where you begin Act 3: its `inbox_client.py`
is the 1.01 hardened client with the 1.02 additions marked as guided
TODO steps, and its `compare_providers.py` stops at the starting
line until those steps exist — that stop is deliberate.

## The exercise

In `exercise/`: implement the routing rule and the routed run.
Full statement in `exercise/README.md`; the graded starting point is
`exercise/router.py`, the harness is `exercise/router_harness.py`,
and the worked answer is in `exercise/solution/`.

### Measurable pass condition

Run, from `exercise/`:

    python3 router_harness.py

It must print PASS for all six scenarios and exit 0:

1. **config_switch** — one interface answers the same question on all
   three providers, usage reported each time.
2. **cost_exact** — the cost the client charges for an exchange
   equals the cost computed from the *server-published* prices.
3. **context_guard** — the oversize brief to sprout raises
   `ContextTooLargeError`, and the server saw exactly 1 request.
4. **routing_rule** — the workload routes exactly: sprout, sprout,
   oracle, atlas, sprout, atlas.
5. **routing_saves** — the routed total is at most half the
   all-oracle total on the same workload (measured: 43.7%).
6. **provider_down** — with oracle's server stopped, the call raises
   `ProviderUnavailableError` naming the provider; nothing is
   silently re-routed.

Against the starter, scenarios 4 and 5 fail and the other four pass —
the interface is given; the rule, and the saving it buys, are the
exercise:

    python3 router_harness.py --router router.py
