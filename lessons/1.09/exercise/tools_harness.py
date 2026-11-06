"""The tools harness for Exercise 1.09.

    python3 tools_harness.py                          # grade the worked solution
    python3 tools_harness.py --dispatcher dispatch.py  # grade yours

Loads a dispatcher module (it must define run_task(calls,
store) -> log) and runs it over the 16 tasks in tasks.json.
The proposed calls are emitted from the task specs by the
lesson's own lab (../solution/tool_lab.py -- the emission
rules are the shared contract; they are not yours to
edit), each task against a fresh store.

The bars (from the lesson, stated before any code):

  safety      ZERO invalid executions and ZERO crashed
              tasks. An invalid execution is a write
              sitting in the store in a form the tool's
              schema forbids (a label outside the closed
              set, a draft body past the cap) -- downstream
              code reads the store, and it trusts it.
  completion  at least 10 of the 16 tasks reach their
              gold end state exactly (labels exact, drafts
              byte for byte, gold facts in the returned
              results). Refusal is legitimate -- six of
              these tasks cannot be completed honestly --
              and priced: it is spent from this budget.
  precision   at least 0.90 of the writes on file match
              gold exactly. The one planted judgement
              error (ex-12) caps this below 1.0 for every
              dispatcher; the bar is set under the ceiling.

Exit 0 only when all three bars are met.
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOLUTION = os.path.join(HERE, "..", "solution")
sys.path.insert(0, SOLUTION)

import tool_lab  # noqa: E402  (the shared emission rules)
import tools  # noqa: E402  (the shared registry + store)

DOC = json.load(open(os.path.join(HERE, "tasks.json")))
TASKS = DOC["tasks"]
COMPLETION_BAR = 10
PRECISION_BAR = 0.90


def load_dispatcher(path):
    spec = importlib.util.spec_from_file_location(
        "dispatcher_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_task


def grade_task(task, store, log):
    gold = task["gold"]
    labels_ok = store.labels == gold.get("labels", {})
    gold_drafts = gold.get("drafts", [])
    drafts_ok = (
        len(store.drafts) == len(gold_drafts)
        and all(any(d["message_id"] == g["message_id"]
                    and d["body"] == g["body"]
                    for d in store.drafts)
                for g in gold_drafts))
    digest = json.dumps(log.get("results", []))
    facts_ok = all(f in digest for f in gold.get("facts", []))
    return labels_ok and drafts_ok and facts_ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dispatcher", default=None,
                        help="dispatcher module to grade (default: "
                             "the worked solution in solution/)")
    args = parser.parse_args()
    path = args.dispatcher or os.path.join(HERE, "solution",
                                           "dispatch.py")
    run_task = load_dispatcher(path)

    print("dispatcher under test: {}".format(path))
    correct, wrong, incomplete, crashed = [], [], [], []
    invalid = 0
    writes = writes_right = 0
    for task in TASKS:
        store = tools.Store.from_records()
        calls = [tool_lab.emit(spec) for spec in task["calls"]]
        try:
            log = run_task(calls, store)
        except Exception as exc:  # a dispatcher that dies files chaos
            crashed.append((task["id"], repr(exc)))
            continue
        # safety: scan the end state for forbidden forms
        bad = [v for v in store.labels.values()
               if v not in tools.LABELS]
        bad += [d for d in store.drafts if len(d["body"]) > 500]
        invalid += len(bad)
        # precision: the writes on file vs gold
        gold = task["gold"]
        for mid, label in store.labels.items():
            writes += 1
            writes_right += gold.get("labels", {}).get(mid) == label
        for d in store.drafts:
            writes += 1
            writes_right += any(
                d["message_id"] == g["message_id"]
                and d["body"] == g["body"]
                for g in gold.get("drafts", []))
        if grade_task(task, store, log):
            correct.append(task["id"])
        elif log.get("refused"):
            incomplete.append(task["id"])
        else:
            wrong.append(task["id"])

    print("{:10s} {}".format("task", "outcome"))
    for task in TASKS:
        cid = task["id"]
        if cid in correct:
            out = "correct"
        elif cid in dict(crashed):
            out = "CRASHED " + dict(crashed)[cid]
        elif cid in wrong:
            out = "wrong (disposed; the end state is not gold)"
        else:
            out = "incomplete (a call refused, by name)"
        print("{:10s} {}".format(cid, out))
    print()
    precision = writes_right / writes if writes else 0.0
    rows = [
        ("safety", "no invalid executions, no crashes",
         invalid == 0 and not crashed,
         "{} invalid, {} crashed".format(invalid, len(crashed))),
        ("completion",
         "tasks at gold >= {} of {}".format(COMPLETION_BAR, len(TASKS)),
         len(correct) >= COMPLETION_BAR,
         "{} correct".format(len(correct))),
        ("precision", "writes matching gold >= {:.2f}".format(
            PRECISION_BAR), precision >= PRECISION_BAR,
         "{:.3f} ({}/{})".format(precision, writes_right, writes)),
    ]
    failed = 0
    for name, label, ok, score in rows:
        failed += not ok
        print("{:10s} {:38s} {:>14s}  {}".format(
            name, label, score, "PASS" if ok else "FAIL"))
    print()
    if failed:
        print("{} of {} bars missed. The failures above are the "
              "syllabus.".format(failed, len(rows)))
        return 1
    print("All {} bars met: nothing invalid landed, the "
          "completion honest, the writes right.".format(len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
