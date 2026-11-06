"""STARTER -- the routing rule is yours to write (Lesson 1.02 exercise).

Given (already working, do not rebuild it): the provider interface in
../solution/inbox_client.py, the three mock provider servers, and the
six-task workload in ../solution/workload.py. The harness passes
scenarios 1, 2, 3 and 6 against this starter untouched.

Your task: implement the routing rule from the exercise README --

    1. A summary goes to ORACLE.
    2. Any other task whose prompt is larger than a quick question
       (over 200 estimated tokens -- it carries a document) goes to
       ATLAS.
    3. Everything else goes to SPROUT.

-- plus run_routed, which executes a workload through a dict of
ProviderClients and returns one log row per task.

Grade yourself with:  python3 router_harness.py --router router.py
The worked answer is in solution/router.py, in this folder. Try first.
"""

from workload import estimate_prompt_tokens

DOCUMENT_TOKENS = 200


def choose_provider(task):
    """Return "sprout", "atlas" or "oracle" for one workload task."""
    # TODO 1: summaries go to the frontier tier. Look at task["kind"].
    # TODO 2: document-carrying tasks (estimate_prompt_tokens over
    #         DOCUMENT_TOKENS) go to the balanced tier.
    # TODO 3: everything else goes to the cheap tier.
    raise NotImplementedError("choose_provider is the exercise -- see README.md")


def run_routed(tasks, clients):
    """Run every task on its rule-chosen provider; return log rows.

    Each row: {"task", "provider", "usage", "cost_usd", "elapsed_s"},
    read from the client's last_usage / last_cost_usd / last_elapsed_s
    after its chat call.
    """
    raise NotImplementedError("run_routed is the exercise -- see README.md")
