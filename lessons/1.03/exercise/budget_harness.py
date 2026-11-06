"""Budget harness for the AIE 1.03 exercise.

Usage:
    python3 budget_harness.py [--budget PATH]

Default budget module: the exercise solution next to this file
(exercise/solution/budget.py). Point --budget at the starter
(exercise/budget.py) and scenarios 3 and 4 fail by design: the
counter, the guard and the budget are given; the policy -- ranking,
truncation, and a loss log that accounts for every cut -- is the
exercise.

The harness starts the three mock provider servers (from
../solution/), runs six scenarios, and asserts on counted tokens,
loss-log completeness, server request counts and exception types.
One PASS/FAIL line per scenario; exit 0 only if all six pass.
Standard library only.
"""

import argparse
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOLUTION = os.path.join(HERE, "..", "solution")
sys.path.insert(0, SOLUTION)

from budget import BudgetedProviderClient, BudgetExceededError  # noqa: E402
from documents import (  # noqa: E402
    QUESTION,
    SYSTEM,
    doc_block,
    fixed_messages,
    load_documents,
    rank_documents,
)
from inbox_client import ContextTooLargeError, ProviderClient  # noqa: E402
from providers_common import ProviderServers, request_count  # noqa: E402
from tokenizer import count_messages_tokens, count_tokens, word_count  # noqa: E402

DEFAULT_BUDGET = os.path.join(HERE, "solution", "budget.py")

WINDOW = 4000
RESERVE = 400
BUDGET = WINDOW - RESERVE

RESULTS = []


def report(ok, label, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ((" -- " + detail) if detail else ""))
    RESULTS.append(ok)


def load_budget(path):
    spec = importlib.util.spec_from_file_location("budget_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scenario_counter_honesty():
    label = "1 counter_honesty: the token meter is exact, deterministic, and never below words"
    try:
        q = "When does Project Aurora launch?"
        assert count_tokens(q) == 10, "question counts %d, expected 10" % count_tokens(q)
        assert count_tokens(q) == count_tokens(q)
        for doc in load_documents():
            block = doc_block(doc["name"], doc["text"])
            assert count_tokens(block) >= word_count(block), doc["name"]
        report(True, label, "question = 10 tokens / 5 words")
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_budget_never_exceeded(budget):
    label = "2 budget_never_exceeded: the fitted prompt fits, is sent once, and the server agrees"
    try:
        ranked = rank_documents(load_documents())
        messages, _losses = budget.fit_documents(ranked, BUDGET)
        counted = count_messages_tokens(messages)
        assert counted <= BUDGET, "counted %d > budget %d" % (counted, BUDGET)
        client = BudgetedProviderClient("atlas", reserve_tokens=RESERVE)
        before = request_count("atlas")
        answer = client.chat(messages)
        assert answer, "empty answer"
        assert request_count("atlas") - before == 1
        assert client.last_usage["prompt_tokens"] <= counted, (
            "server metered %d words > counted %d tokens"
            % (client.last_usage["prompt_tokens"], counted)
        )
        report(True, label, "counted %d tokens; server usage %d words"
               % (counted, client.last_usage["prompt_tokens"]))
        return messages
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])
        return None


def scenario_loss_log_complete(budget):
    label = "3 loss_log_complete: every cut is logged, and the log's numbers add up"
    try:
        documents = load_documents()
        ranked = rank_documents(documents)
        messages, losses = budget.fit_documents(ranked, BUDGET)
        user_text = messages[-1]["content"]
        by_name = {d["name"]: d for d in documents}
        logged = {}
        for loss in losses:
            assert loss["document"] not in logged, "duplicate loss: " + loss["document"]
            logged[loss["document"]] = loss
            full = count_tokens(doc_block(loss["document"], by_name[loss["document"]]["text"]))
            assert loss["kept_tokens"] + loss["dropped_tokens"] == full, (
                loss["document"] + ": kept+dropped != full count"
            )
            if loss["action"] == "skipped":
                assert loss["kept_tokens"] == 0
                assert doc_block(loss["document"], by_name[loss["document"]]["text"]) not in user_text
            elif loss["action"] == "truncated":
                assert 0 < loss["kept_tokens"] < full
            else:
                raise AssertionError("unknown action " + loss["action"])
        for doc in documents:
            whole = doc_block(doc["name"], doc["text"]) in user_text
            assert whole == (doc["name"] not in logged), (
                doc["name"] + ": in prompt whole=%s, logged=%s" % (whole, doc["name"] in logged)
            )
        report(True, label, "%d losses logged" % len(losses))
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_policy_fills(budget):
    label = "4 policy_fills: relevance order respected and the window actually filled"
    try:
        ranked = rank_documents(load_documents())
        messages, losses = budget.fit_documents(ranked, BUDGET)
        counted = count_messages_tokens(messages)
        assert counted >= BUDGET - 100, "fitted %d leaves the window unfilled (budget %d)" % (counted, BUDGET)
        user_text = messages[-1]["content"]
        whole = [d["name"] for d in ranked if doc_block(d["name"], d["text"]) in user_text]
        assert whole == [d["name"] for d in ranked[: len(whole)]], (
            "kept-whole set is not a prefix of the ranking: " + ", ".join(whole)
        )
        trunc = {l["document"]: l for l in losses if l["action"] == "truncated"}
        assert "vendor_review.txt" in trunc and trunc["vendor_review.txt"]["kept_tokens"] >= 300, (
            "vendor_review should be truncated with a useful prefix kept"
        )
        report(True, label, "fitted %d of %d; whole: %s" % (counted, BUDGET, ", ".join(whole)))
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_fixed_parts(budget):
    label = "5 fixed_parts: the system message and the question are never shed"
    try:
        ranked = rank_documents(load_documents())
        messages, _losses = budget.fit_documents(ranked, BUDGET)
        assert messages[0] == {"role": "system", "content": SYSTEM}
        assert messages[-1]["content"].startswith(QUESTION)
        report(True, label)
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def scenario_naive_and_guard():
    label = "6 naive_and_guard: the naive prompt exceeds locally and hits the real wall at sprout"
    try:
        documents = load_documents()
        naive = fixed_messages([doc_block(d["name"], d["text"]) for d in documents])
        counted = count_messages_tokens(naive)
        assert counted > BUDGET, "naive counts %d, expected over %d" % (counted, BUDGET)
        before = request_count("atlas")
        try:
            BudgetedProviderClient("atlas", reserve_tokens=RESERVE).chat(naive)
            raise AssertionError("budgeted client sent an over-budget prompt")
        except BudgetExceededError:
            pass
        assert request_count("atlas") - before == 0, "the guard sent a request"
        before = request_count("sprout")
        try:
            ProviderClient("sprout").chat(naive)
            raise AssertionError("sprout accepted the naive prompt")
        except ContextTooLargeError:
            pass
        assert request_count("sprout") - before == 1
        report(True, label, "naive counts %d tokens" % counted)
    except Exception as exc:
        report(False, label, type(exc).__name__ + ": " + str(exc)[:120])


def main():
    parser = argparse.ArgumentParser(description="AIE 1.03 budget harness.")
    parser.add_argument("--budget", default=DEFAULT_BUDGET)
    args = parser.parse_args()
    budget = load_budget(args.budget)
    print("budget module under test: " + args.budget)

    scenario_counter_honesty()
    with ProviderServers():
        scenario_budget_never_exceeded(budget)
        scenario_loss_log_complete(budget)
        scenario_policy_fills(budget)
        scenario_fixed_parts(budget)
        scenario_naive_and_guard()

    passed = sum(RESULTS)
    print("RESULT: %d/%d scenarios passed" % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) == 6 else 1


if __name__ == "__main__":
    sys.exit(main())
