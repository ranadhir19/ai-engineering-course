"""The settings harness for Exercise 1.07.

    python3 sampling_harness.py                        # grade the worked solution
    python3 sampling_harness.py --settings sampling.py  # grade the starter (yours)

Loads a settings module (it must define SETTINGS, one setting
per task family: temperature, top_k, top_p, vote_k) and runs
the lesson's three suites (tasks.json) through the sampling
lab (../solution/sampling_lab.py -- seeded, its rules printed
in its docstring, so the numbers you see are the numbers there
are). Case metrics are averaged over 25 replicas: a single
replica's vote is itself a draw, and grading one would grade
luck.

The bars (from the lesson, stated before any code):

  extraction     filed-answer accuracy >= 0.90 over 12 cases.
                 Triage files legal and financial mail; a filer
                 that is right seven times in ten (the default's
                 measured score) is not a filer.
  grading        filed exact match >= 0.70 AND mean absolute
                 error <= 0.35 over 10 cases. A grade is an
                 audit record: it must be the same grade when
                 the run is repeated, and when it misses it
                 must miss by a little.
  brainstorming  distinct >= 8.0 of 12 lines in 300 draws,
                 top-1 share <= 0.45, off-brief <= 3 per 300.
                 Variety is the product -- but the catalogue is
                 finite, one line must not swallow the send,
                 and the off-brief tail is a defect, not spice.

Exit 0 only when every bar is met. The trap is built in and is
the lesson: no single global setting meets all three families'
bars -- greedy starves brainstorming, temperature 1 starves
the filer and the grader. Per-task settings, defended per
task, are the only way through.
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOLUTION = os.path.join(HERE, "..", "solution")
sys.path.insert(0, SOLUTION)

import sampling  # noqa: E402  (the lesson's measurement code)

TASKS = json.load(open(os.path.join(HERE, "tasks.json")))

BARS = {
    "extraction": ("case_accuracy", ">=", 0.90),
    "grading_exact": ("case_exact", ">=", 0.70),
    "grading_mae": ("case_mae", "<=", 0.35),
    "brain_distinct": ("distinct", ">=", 8.0),
    "brain_top": ("top_share", "<=", 0.45),
    "brain_off": ("offbrief_per_n", "<=", 3.0),
}


def load_settings(path):
    spec = importlib.util.spec_from_file_location("settings_under_test",
                                                  path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SETTINGS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", default=None,
                        help="settings module to grade (default: the "
                             "worked solution in solution/)")
    args = parser.parse_args()
    path = args.settings or os.path.join(HERE, "solution", "sampling.py")
    settings = load_settings(path)
    scores = sampling.score_settings(TASKS, settings)

    rows = [
        ("extraction", "filed-answer accuracy >= 0.90",
         scores["extraction"]["case_accuracy"], BARS["extraction"]),
        ("grading", "filed exact match >= 0.70",
         scores["grading"]["case_exact"], BARS["grading_exact"]),
        ("grading", "mean absolute error <= 0.35",
         scores["grading"]["case_mae"], BARS["grading_mae"]),
        ("brainstorming", "distinct lines >= 8.0 of 12",
         scores["brainstorming"]["distinct"], BARS["brain_distinct"]),
        ("brainstorming", "top-1 share <= 0.45",
         scores["brainstorming"]["top_share"], BARS["brain_top"]),
        ("brainstorming", "off-brief <= 3 per 300 draws",
         scores["brainstorming"]["offbrief_per_n"], BARS["brain_off"]),
    ]
    print("settings under test: {}".format(path))
    print("{:14s} {:38s} {:>8s}  {}".format("task", "bar", "score",
                                            "verdict"))
    failed = 0
    for task, label, score, (_key, op, bar) in rows:
        ok = score >= bar if op == ">=" else score <= bar
        failed += not ok
        print("{:14s} {:38s} {:8.3f}  {}".format(
            task, label, score, "PASS" if ok else "FAIL"))
    print()
    if failed:
        print("{} of {} bars missed. The failures above are the "
              "syllabus.".format(failed, len(rows)))
        return 1
    print("All {} bars met: every task at a setting defended by "
          "its own measurement.".format(len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
