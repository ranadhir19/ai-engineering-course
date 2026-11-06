# Exercise 1.02 — Route the workload: a rule, and the saving it buys

The interface is given. `ProviderClient` (in `../solution/`) already
talks to all three providers, prices every call and names its
failures. What no library can give you is the policy: **which task
deserves which provider.** That policy is this exercise, and like
every policy in this course it is graded by a harness, not by taste.

## The task

In `router.py` in this folder, implement two functions:

- `choose_provider(task)` — return the provider name for one task,
  under exactly this rule:
  1. A summary (`task["kind"] == "summary"`) goes to **oracle**.
     Summaries are output-heavy and quality-critical; that is what
     the frontier tier is for.
  2. Any other task whose estimated prompt size
     (`estimate_prompt_tokens(task["messages"])`) is over
     **200 tokens** — it carries a document — goes to **atlas**.
  3. Everything else goes to **sprout**.
- `run_routed(tasks, clients)` — run each task on its chosen
  provider and return one log row per task:
  `{"task", "provider", "usage", "cost_usd", "elapsed_s"}`, read from
  the client after its call.

Rules of the road:

- Never send a task to a provider whose context limit it exceeds.
  Check that the rule above cannot do it, and be able to say why.
- No silent fallback anywhere: if the chosen provider is down, the
  `ProviderUnavailableError` propagates. Routing around a failure is
  a different policy, adopted openly, not smuggled into this one.
- Standard library only; the workload and its token estimates come
  from `../solution/workload.py` (already importable).

## How you are graded

    python3 router_harness.py

The harness starts the three provider servers and asserts on
answers, exception types, exact request counts (via `/__count`),
charged costs (recomputed from the server-published prices) and the
routed total:

1. `config_switch` — the interface answers on all three providers.
2. `cost_exact` — charged cost equals server-published pricing.
3. `context_guard` — oversize to sprout: `ContextTooLargeError`,
   exactly 1 request.
4. `routing_rule` — routes are exactly sprout, sprout, oracle,
   atlas, sprout, atlas.
5. `routing_saves` — routed total at most half the all-oracle total
   (the worked solution measures 43.7%).
6. `provider_down` — oracle stopped: `ProviderUnavailableError`
   naming the provider, no silent re-route.

Exit 0 with 6/6 PASS is a pass. Run it against the starter first to
see the honest baseline — scenarios 4 and 5 fail there:

    python3 router_harness.py --router router.py

The worked answer lives in `solution/router.py` in this folder. Try
the exercise before you read it; then be able to explain why the
summary does not go to the cheap tier even though its prompt would
fit, in one sentence, using the output prices.
