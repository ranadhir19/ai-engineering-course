"""The records harness for Exercise 1.08.

    python3 records_harness.py                        # grade the worked solution
    python3 records_harness.py --extractor extract.py  # grade yours

Loads an extractor module (it must define extract(reply_text)
-> record dict | None) and runs it over the 16 raw replies in
records.json, grading against the lesson's schema
(../solution/structured.py -- record@1.0.0 is the shared
contract; it is not yours to edit).

The bars (from the lesson, stated before any code):

  validity   EVERY emitted record validates against the
             schema. One invalid emission fails the run --
             downstream code files what you emit.
  yield      at least 13 of the 16 replies produce a record.
             Rejection is a legitimate move with a price:
             three of these replies (a missing required key,
             an enum synonym, a truncated reply) cannot be
             filed honestly, and no extractor may file them.
  accuracy   field accuracy at or above 0.95 over the emitted
             records: every field exact, except the summary,
             which is graded on carrying the case's printed
             key phrase. A constant, always-valid record --
             the schema-gamer's move -- scores about 0.2 and
             fails here, which is what this bar is for.

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

import structured  # noqa: E402  (the shared contract)

DOC = json.load(open(os.path.join(HERE, "records.json")))
CASES = DOC["cases"]
YIELD_BAR = 13
ACCURACY_BAR = 0.95


def load_extractor(path):
    spec = importlib.util.spec_from_file_location("extractor_under_test",
                                                  path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.extract


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extractor", default=None,
                        help="extractor module to grade (default: the "
                             "worked solution in solution/)")
    args = parser.parse_args()
    path = args.extractor or os.path.join(HERE, "solution", "extract.py")
    extract = load_extractor(path)

    print("extractor under test: {}".format(path))
    filed, invalid, rejected, crashed = {}, [], [], []
    for case in CASES:
        try:
            rec = extract(case["reply"])
        except Exception as exc:  # an extractor that dies files nothing
            crashed.append((case["id"], repr(exc)))
            continue
        if rec is None:
            rejected.append(case["id"])
            continue
        errors = structured.validate(rec)
        if errors:
            invalid.append((case["id"], errors[0]))
        else:
            filed[case["id"]] = rec

    acc, wrong = structured.field_accuracy(
        filed, [{"id": c["id"], "gold": c["gold"],
                 "summary_key": c["summary_key"]} for c in CASES])
    print("{:10s} {:8s} {}".format("case", "outcome", "detail"))
    for case in CASES:
        cid = case["id"]
        if cid in filed:
            bad = [f for c, f in wrong if c == cid]
            print("{:10s} {:8s} {}".format(
                cid, "filed", ("wrong: " + ", ".join(bad)) if bad else ""))
        elif cid in dict(invalid):
            print("{:10s} {:8s} {}".format(cid, "INVALID",
                                          dict(invalid)[cid]))
        elif cid in dict(crashed):
            print("{:10s} {:8s} {}".format(cid, "CRASHED",
                                          dict(crashed)[cid]))
        else:
            print("{:10s} {:8s}".format(cid, "rejected"))
    print()
    rows = [
        ("validity", "no invalid emissions", not invalid and not crashed,
         "{} invalid, {} crashed".format(len(invalid), len(crashed))),
        ("yield", "records filed >= {} of {}".format(YIELD_BAR, len(CASES)),
         len(filed) >= YIELD_BAR, "{} filed".format(len(filed))),
        ("accuracy", "field accuracy >= {:.2f}".format(ACCURACY_BAR),
         acc >= ACCURACY_BAR, "{:.3f}".format(acc)),
    ]
    failed = 0
    for name, label, ok, score in rows:
        failed += not ok
        print("{:10s} {:34s} {:>10s}  {}".format(
            name, label, score, "PASS" if ok else "FAIL"))
    print()
    if failed:
        print("{} of {} bars missed. The failures above are the "
              "syllabus.".format(failed, len(rows)))
        return 1
    print("All {} bars met: every filed record valid, the yield "
          "honest, the fields right.".format(len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
