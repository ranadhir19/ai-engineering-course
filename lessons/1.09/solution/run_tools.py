"""The measurements for Lesson 1.09, in six sections.

    python3 run_tools.py           # all six sections
    python3 run_tools.py agent     # or one at a time

Sections: the wild (what the model actually proposes --
the first-emission census), trust (the found executor),
agent (the shipped disposal, agent@1.0.0, with the
error-feedback loop), strict (fail-fast), parallel (what
multi-call turns buy), and the shipped summary beside the
executor it replaces. Every number is computed here from
tool_tasks.json via tool_lab, tools and agent; nothing is
typed in.
"""

import json
import os
import sys
from collections import Counter

import agent
import tool_lab
import tools

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = json.load(open(os.path.join(HERE, "tool_tasks.json")))
TASKS = DOC["tasks"]
N = len(TASKS)


def _run_all(strategy):
    runs = {}
    for task in TASKS:
        store = tools.Store.from_records()
        run = agent.RUNNERS[strategy](task, store)
        run["outcome"] = agent.grade(task, store, run)
        runs[task["id"]] = (run, store)
    return runs


def _summary(runs):
    outcomes = Counter(r["outcome"] for r, _ in runs.values())
    return {
        "correct": outcomes.get("correct", 0),
        "wrong": outcomes.get("wrong", 0),
        "failed": outcomes.get("failed", 0),
        "invalid_executions": sum(r["invalid_executions"]
                                  for r, _ in runs.values()),
        "crashed": sum(1 for r, _ in runs.values() if r["crashed"]),
        "refused": sum(1 for r, _ in runs.values() if r["refused"]),
        "model_calls": sum(r["model_calls"] for r, _ in runs.values()),
        "retries": sum(r["retries"] for r, _ in runs.values()),
        "price": sum(r["price"] for r, _ in runs.values()),
    }


def _print_runs(runs):
    for task in TASKS:
        run, _ = runs[task["id"]]
        note = ""
        if run["crashed"]:
            note = " (crashed)"
        elif run["refused"]:
            note = " (refused at {})".format(run["refused"][0])
        elif run["failed_at"]:
            note = " (failed at {})".format(run["failed_at"]["name"])
        print("  {}  {}{}".format(task["id"], run["outcome"], note))


def section_wild():
    print("=" * 72)
    print("1. THE WILD -- what the model proposes (24 tasks)")
    print("=" * 72)
    census = agent.first_emission_census(TASKS)
    for task in TASKS:
        parts = []
        for turn in task["turns"]:
            for spec in turn:
                d = spec.get("defects", [])
                parts.append("{}: {}".format(
                    spec["name"], ", ".join(d) if d else "clean"))
        print("  {}  {}".format(task["id"], " | ".join(parts)))
    print()
    print("  planned calls: {}; first emissions formally defective: "
          "{} ({:.1f}%)".format(
              census["total"], census["defective"],
              100.0 * census["defective"] / census["total"]))
    kinds = {k: v for k, v in sorted(census.items())
             if k not in ("total", "defective", "clean", "world")}
    print("  defect census: " + ", ".join(
        "{} x{}".format(k, v) for k, v in kinds.items()))
    print("  formally clean but wrong in the world (bad id): "
          "{}".format(census["world"]))
    print("  every defect here is in the arguments string or the")
    print("  values -- the model's judgement is a separate question,")
    print("  and three tasks carry it planted (task-13, task-18,")
    print("  task-22). No dispatcher in this lesson touches it.")


def section_trust():
    print("=" * 72)
    print("2. TRUST -- the found executor (parse-and-pray)")
    print("=" * 72)
    runs = _run_all("trust")
    _print_runs(runs)
    s = _summary(runs)
    print()
    print("  correct {}/{}; wrong {}; failed {}".format(
        s["correct"], N, s["wrong"], s["failed"]))
    print("  tasks crashed by an exception: {}".format(s["crashed"]))
    print("  INVALID EXECUTIONS (writes that landed in forms the")
    print("  schema forbids): {}".format(s["invalid_executions"]))
    for task in TASKS:
        run, _ = runs[task["id"]]
        for name, why in run["invalid_detail"]:
            print("    {} {}: {}".format(task["id"], name, why))
    print("  model calls: {}; batch price on atlas: ${:.6f}".format(
        s["model_calls"], s["price"]))
    print("  nothing here was ever validated, so nothing here was")
    print("  ever refused -- the failures are silent drops, crashes,")
    print("  and two writes sitting in the store in forbidden forms.")


def section_agent():
    print("=" * 72)
    print("3. AGENT -- agent@1.0.0 (validate, dispose, hand errors back)")
    print("=" * 72)
    runs = _run_all("agent")
    _print_runs(runs)
    s = _summary(runs)
    print()
    print("  correct {}/{}; wrong {}; failed {}".format(
        s["correct"], N, s["wrong"], s["failed"]))
    print("  invalid executions: {}".format(s["invalid_executions"]))
    print("  correction rounds used: {}; model calls: {} "
          "({:.2f} per task)".format(
              s["retries"], s["model_calls"], s["model_calls"] / N))
    print("  batch price on atlas: ${:.6f}".format(s["price"]))
    print("  every defective first emission was disposed by name --")
    print("  parse, validate, registry, execute -- and the model")
    print("  corrected exactly the named defect. The three wrong")
    print("  tasks are the planted judgement errors: disposed")
    print("  perfectly, wrong anyway. That is the ceiling.")


def section_strict():
    print("=" * 72)
    print("4. STRICT -- fail-fast (validate the turn, refuse on defect)")
    print("=" * 72)
    runs = _run_all("strict")
    _print_runs(runs)
    s = _summary(runs)
    print()
    print("  correct {}/{}; wrong {}; failed (refused/aborted) {}".format(
        s["correct"], N, s["wrong"], s["failed"]))
    print("  invalid executions: {}".format(s["invalid_executions"]))
    print("  model calls: {}; batch price on atlas: ${:.6f}".format(
        s["model_calls"], s["price"]))
    print("  nothing invalid ever lands -- and tasks die on defects")
    print("  a feedback loop repairs in one round. Fail-fast")
    print("  cannot tell a clerical defect from a dangerous one; it")
    print("  treats the trailing comma like the unknown tool.")


def section_parallel():
    print("=" * 72)
    print("5. PARALLEL -- calls that ride in one turn")
    print("=" * 72)
    turns = sum(len(t["turns"]) for t in TASKS)
    calls = sum(agent._planned_calls(t) for t in TASKS)
    multi = [t["id"] for t in TASKS
             if any(len(turn) > 1 for turn in t["turns"])]
    print("  planned calls: {}; model turns that carry them: "
          "{}".format(calls, turns))
    print("  multi-call turns: {} ({} tasks)".format(
        calls - turns, len(multi)))
    print("  tasks with a parallel turn: " + ", ".join(multi))
    print("  the calls in a parallel turn are independent by"
          " construction --")
    print("  labels for two different messages, a label and a draft --")
    print("  and the dispatcher disposes each on its own merits: in")
    print("  task-16 one of the pair arrives as a Python repr and is")
    print("  corrected while its sibling executes untouched.")


def section_shipped():
    print("=" * 72)
    print("6. THE SHIPPED DISPOSAL -- agent@1.0.0 vs the found executor")
    print("=" * 72)
    trust = _summary(_run_all("trust"))
    shipped = _summary(_run_all("agent"))
    strict = _summary(_run_all("strict"))
    print("  {:28s} {:>8s} {:>8s} {:>8s}".format(
        "", "trust", "strict", "agent"))
    for label, key in (("tasks correct", "correct"),
                       ("tasks wrong (judgement)", "wrong"),
                       ("tasks failed", "failed"),
                       ("invalid executions", "invalid_executions"),
                       ("model calls", "model_calls")):
        print("  {:28s} {:>8d} {:>8d} {:>8d}".format(
            label, trust[key], strict[key], shipped[key]))
    print("  {:28s} {:>8.6f} {:>8.6f} {:>8.6f}".format(
        "batch price $", trust["price"], strict["price"],
        shipped["price"]))
    print()
    print("  the wrong three are the same three under every strategy:")
    print("  task-13 (a label), task-18 (a search's first hit),")
    print("  task-22 (a draft's addressee) -- the model's judgement,")
    print("  filed faithfully by machinery that did its whole job.")
    print("  form and authority are closed by disposal. Truth is not:")
    print("  it is the next lessons' problem (validation at the")
    print("  boundary, measurement), not this one's failure.")


SECTIONS = {"wild": section_wild, "trust": section_trust,
            "agent": section_agent, "strict": section_strict,
            "parallel": section_parallel, "shipped": section_shipped}


def main():
    names = sys.argv[1:] or list(SECTIONS)
    for name in names:
        SECTIONS[name]()
        print()


if __name__ == "__main__":
    main()
