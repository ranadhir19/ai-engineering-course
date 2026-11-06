"""The routing rule for Lesson 1.02 (worked solution).

One interface, three providers, and a rule the caller owns:

    1. A summary goes to ORACLE. Summaries are the output-heavy,
       quality-critical tasks; that is what the frontier tier is for.
    2. Any other task whose prompt is larger than a quick question
       (over 200 estimated tokens -- it carries a document) goes to
       ATLAS, the balanced tier whose context window holds it.
    3. Everything else -- the short questions that are most of real
       traffic -- goes to SPROUT, the cheap tier.

The rule only ever sends a task to a provider whose context limit
holds it: sprout receives at most 200-token prompts (limit 600),
atlas at most the brief (limit 4000), oracle takes the rest
(limit 20000). Routing is a policy; this file is where it lives,
in the open, where it can be read, tested and changed.
"""

from workload import estimate_prompt_tokens

DOCUMENT_TOKENS = 200


def choose_provider(task):
    """Return the provider name for one workload task."""
    if task["kind"] == "summary":
        return "oracle"
    if estimate_prompt_tokens(task["messages"]) > DOCUMENT_TOKENS:
        return "atlas"
    return "sprout"


def run_routed(tasks, clients):
    """Run every task on its rule-chosen provider.

    ``clients`` maps provider name -> ProviderClient. Returns a list
    of log rows: task id, provider, usage, dollars, seconds.
    """
    rows = []
    for task in tasks:
        name = choose_provider(task)
        client = clients[name]
        client.chat(task["messages"])
        rows.append(
            {
                "task": task["id"],
                "provider": name,
                "usage": dict(client.last_usage or {}),
                "cost_usd": client.last_cost_usd,
                "elapsed_s": client.last_elapsed_s,
            }
        )
    return rows
