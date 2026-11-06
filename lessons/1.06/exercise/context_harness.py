"""The scenario harness for Exercise 1.06.

    python3 context_harness.py                       # grade the worked solution
    python3 context_harness.py --assembler context.py  # grade the starter

Loads the module under test (it must define
``assemble(scenario) -> (messages, report)``) and runs every
scenario in scenarios.json through this lesson's context lab
(../solution/context_lab.py -- deterministic, its rules printed
in its docstring, so the score you see is the score there is).

Each scenario is graded on the lesson's four checks:

  budget          the assembled window, counted with the pack's
                  BPE counter, is within the scenario's budget;
  instruction     the standing instruction -- answer only from
                  the context, say "I don't know" when you
                  cannot -- is present in the system message;
  answer          the lab's answer to the scenario's question
                  equals the gold answer;
  no_silent_drop  every input item (each example, document and
                  history turn) is either visibly present in the
                  window or named in report["items"] with what
                  was done with it. An item that vanished without
                  a line in the report fails the scenario.

Pass mark (from the lesson, stated before any code): all four
checks on all ten scenarios. Anything less is a policy with a
hole in it, and the report shows which hole. Exit 0 at the pass
mark, 1 below it.
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOLUTION = os.path.join(HERE, "..", "solution")
sys.path.insert(0, SOLUTION)

import context_lab  # noqa: E402
from tokenizer import count_messages_tokens  # noqa: E402

SCENARIOS = json.load(open(os.path.join(HERE, "scenarios.json")))


def _appears(messages, scenario, item_id, blob):
    for example in scenario["examples"]:
        if example["id"] == item_id:
            return example["question"][:40] in blob
    for doc in scenario["documents"]:
        if doc["id"] == item_id:
            return doc["text"][:40] in blob
    for turn in scenario["history"]:
        if turn["id"] == item_id:
            return turn["text"][:40] in blob
    return False


def grade(messages, report, scenario):
    checks = {}
    checks["budget"] = (count_messages_tokens(messages)
                        <= scenario["budget_tokens"])
    checks["instruction"] = (bool(messages)
                             and messages[0].get("role") == "system"
                             and "not in the context"
                             in str(messages[0].get("content", "")))
    checks["answer"] = (context_lab.answer(
        messages, scenario["key_phrases"], scenario["value_kind"])
        == scenario["gold"])
    accounted = {item.get("item")
                 for item in (report or {}).get("items", [])}
    blob = "\n".join(str(m.get("content", "")) for m in messages)
    ids = ({e["id"] for e in scenario["examples"]}
           | {d["id"] for d in scenario["documents"]}
           | {t["id"] for t in scenario["history"]})
    silent = [i for i in ids
              if i not in accounted
              and not _appears(messages, scenario, i, blob)]
    checks["no_silent_drop"] = not silent
    if silent:
        checks["silent_items"] = silent
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assembler", default=None,
                        help="module to grade (default: the worked "
                             "solution in ./solution/)")
    args = parser.parse_args()
    path = args.assembler or os.path.join(HERE, "solution", "context.py")
    spec = importlib.util.spec_from_file_location("candidate", path)
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)

    passed = 0
    for scenario in SCENARIOS:
        messages, report = candidate.assemble(scenario)
        checks = grade(messages, report, scenario)
        ok = all(v for k, v in checks.items() if k != "silent_items")
        passed += ok
        line = "%-15s %s" % (scenario["id"], "PASS" if ok else "FAIL")
        if not ok:
            failed = [k for k, v in checks.items()
                      if k != "silent_items" and not v]
            line += "  (" + ", ".join(failed) + ")"
            if checks.get("silent_items"):
                line += "  silent: " + ", ".join(checks["silent_items"])
        print(line)
    print()
    print("%d/%d scenarios pass all four checks."
          % (passed, len(SCENARIOS)))
    if passed == len(SCENARIOS):
        print("PASS MARK MET: every scenario, every check.")
        return 0
    print("Below the pass mark: all four checks on all ten "
          "scenarios. The failures above are the syllabus.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
