"""Act 4 tutorial driver: the workload, routed by rule vs all-frontier.

Runs the six-task workload twice against the three local providers:
once with every task sent to oracle (the expensive default), once with
router.choose_provider deciding per task. Prints both logs and the
totals, so the saving is a measured number, not a claim.

Run:  python3 route_workload.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from inbox_client import ProviderClient
from providers_common import ProviderServers
from router import run_routed
from workload import build_workload


def _run_all_oracle(tasks):
    client = ProviderClient("oracle")
    rows = []
    for task in tasks:
        client.chat(task["messages"])
        rows.append(
            {
                "task": task["id"],
                "provider": "oracle",
                "usage": dict(client.last_usage or {}),
                "cost_usd": client.last_cost_usd,
                "elapsed_s": client.last_elapsed_s,
            }
        )
    return rows


def _print_log(title, rows):
    print(title)
    total_cost = 0.0
    total_s = 0.0
    for row in rows:
        total_cost += row["cost_usd"]
        total_s += row["elapsed_s"]
        print(
            "  "
            + row["task"]
            + "  "
            + row["provider"].ljust(7)
            + " prompt "
            + str(row["usage"].get("prompt_tokens", 0)).rjust(4)
            + "  completion "
            + str(row["usage"].get("completion_tokens", 0)).rjust(4)
            + "  $"
            + ("%.7f" % row["cost_usd"])
            + "  "
            + ("%.2f" % row["elapsed_s"])
            + "s"
        )
    print("  TOTAL  $" + ("%.7f" % total_cost) + "  " + ("%.2f" % total_s) + "s")
    return total_cost


def main():
    tasks = build_workload()
    with ProviderServers():
        clients = {name: ProviderClient(name) for name in ("sprout", "atlas", "oracle")}
        routed_cost = _print_log("ROUTED (rule: summary->oracle, document->atlas, else sprout)", run_routed(tasks, clients))
        print()
        oracle_cost = _print_log("ALL-ORACLE (every task to the frontier)", _run_all_oracle(tasks))
        print()
        saved = 100.0 * (oracle_cost - routed_cost) / oracle_cost
        print("routed total is %.1f%% of all-oracle -- a %.1f%% saving" % (100.0 * routed_cost / oracle_cost, saved))


if __name__ == "__main__":
    main()
