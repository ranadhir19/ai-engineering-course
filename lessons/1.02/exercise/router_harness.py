"""Routing harness for the AIE 1.02 exercise.

Usage:
    python3 router_harness.py [--router PATH]

Default router: the exercise solution next to this file
(exercise/solution/router.py). Point --router at the starter
(exercise/router.py) and scenarios 4 and 5 fail by design: the
interface, the accounting, the guard and the named failure are given;
the rule -- and the saving it buys -- are the exercise.

The harness starts the three mock provider servers (from
../solution/) on their standard ports, runs six scenarios, and
asserts on answers, exception types, request counts, charged costs
and the routed total. One PASS/FAIL line per scenario; exit 0 only
if all six pass. Standard library only.
"""

import argparse
import importlib.util
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SOLUTION = os.path.join(HERE, "..", "solution")
sys.path.insert(0, SOLUTION)

from inbox_client import (  # noqa: E402
    PROVIDERS,
    ContextTooLargeError,
    ProviderClient,
    ProviderUnavailableError,
)
from providers_common import ProviderServers, request_count  # noqa: E402
from workload import build_workload, estimate_prompt_tokens  # noqa: E402

DEFAULT_ROUTER = os.path.join(HERE, "solution", "router.py")

QUESTION = [
    {"role": "system", "content": "You answer questions about an inbox."},
    {"role": "user", "content": "When does Project Aurora launch?"},
]

EXPECTED_ROUTES = ["sprout", "sprout", "oracle", "atlas", "sprout", "atlas"]

RESULTS = []


def report(ok, label, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ((" -- " + detail) if detail else ""))
    RESULTS.append(ok)


def load_router(path):
    spec = importlib.util.spec_from_file_location("router_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def server_profile(name):
    port = {"sprout": 8771, "atlas": 8772, "oracle": 8773}[name]
    with urllib.request.urlopen(
        "http://127.0.0.1:" + str(port) + "/__profile", timeout=2
    ) as resp:
        return json.loads(resp.read().decode("utf-8"))


def scenario_config_switch():
    label = "1 config_switch: one interface answers on all three providers"
    try:
        for name in ("sprout", "atlas", "oracle"):
            client = ProviderClient(name)
            answer = client.chat(QUESTION)
            assert "November 18" in answer, name + " answer: " + answer[:60]
            assert client.last_usage and client.last_usage["prompt_tokens"] == 11
        report(True, label)
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_cost_exact():
    label = "2 cost_exact: charged cost equals the server-published prices"
    try:
        client = ProviderClient("sprout")
        client.chat(QUESTION)
        profile = server_profile("sprout")
        usage = client.last_usage
        expected = (
            usage["prompt_tokens"] * profile["price_in_per_mtok"]
            + usage["completion_tokens"] * profile["price_out_per_mtok"]
        ) / 1_000_000
        assert abs(client.last_cost_usd - expected) < 1e-12, (
            "charged %.10f, expected %.10f" % (client.last_cost_usd, expected)
        )
        report(True, label, "cost $%.7f" % client.last_cost_usd)
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_context_guard(router):
    label = "3 context_guard: oversize to sprout raises ContextTooLargeError once"
    try:
        tasks = {t["id"]: t for t in build_workload()}
        big = tasks["T3"]["messages"]
        assert estimate_prompt_tokens(big) > PROVIDERS["sprout"]["context_tokens"]
        before = request_count("sprout")
        try:
            ProviderClient("sprout").chat(big)
            raise AssertionError("sprout accepted an oversize prompt")
        except ContextTooLargeError:
            pass
        after = request_count("sprout")
        assert after - before == 1, "sprout saw %d requests, expected 1" % (after - before)
        report(True, label)
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_routing_rule(router):
    label = "4 routing_rule: the workload routes exactly per the rule"
    try:
        tasks = build_workload()
        got = [router.choose_provider(t) for t in tasks]
        assert got == EXPECTED_ROUTES, "routes: " + ", ".join(got)
        clients = {n: ProviderClient(n) for n in ("sprout", "atlas", "oracle")}
        rows = router.run_routed(tasks, clients)
        assert [r["provider"] for r in rows] == EXPECTED_ROUTES
        assert all(r["cost_usd"] is not None and r["cost_usd"] > 0 for r in rows)
        report(True, label, "routes: " + ", ".join(got))
        return rows
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])
        return None


def scenario_routing_saves(router, routed_rows):
    label = "5 routing_saves: routed total is at most half the all-oracle total"
    try:
        assert routed_rows, "no routed rows (scenario 4 failed)"
        tasks = build_workload()
        oracle = ProviderClient("oracle")
        oracle_total = 0.0
        for task in tasks:
            oracle.chat(task["messages"])
            oracle_total += oracle.last_cost_usd
        routed_total = sum(r["cost_usd"] for r in routed_rows)
        ratio = routed_total / oracle_total
        assert ratio <= 0.50, "routed is %.1f%% of all-oracle" % (100 * ratio)
        report(
            True,
            label,
            "routed $%.7f vs all-oracle $%.7f (%.1f%%)"
            % (routed_total, oracle_total, 100 * ratio),
        )
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_provider_down():
    label = "6 provider_down: an unreachable provider is a named error, not a fallback"
    try:
        client = ProviderClient("oracle", timeout_s=2.0)
        try:
            client.chat(QUESTION)
            raise AssertionError("oracle answered while its server was down")
        except ProviderUnavailableError as exc:
            assert "oracle" in str(exc), "error does not name the provider"
        report(True, label)
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def main():
    parser = argparse.ArgumentParser(description="AIE 1.02 routing harness.")
    parser.add_argument("--router", default=DEFAULT_ROUTER)
    args = parser.parse_args()
    router = load_router(args.router)
    print("router under test: " + args.router)

    with ProviderServers():
        scenario_config_switch()
        scenario_cost_exact()
        scenario_context_guard(router)
        routed_rows = scenario_routing_rule(router)
        scenario_routing_saves(router, routed_rows)
    # oracle's server is stopped now: the named-failure scenario.
    scenario_provider_down()

    passed = sum(RESULTS)
    print("RESULT: %d/%d scenarios passed" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) == 6 else 1


if __name__ == "__main__":
    sys.exit(main())
