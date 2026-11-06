"""The boundary harness for Exercise 1.10.

    python3 boundary_harness.py                  # grade the worked solution
    python3 boundary_harness.py --gate admit.py  # grade yours

Loads a gate module (it must define run_gate(crossings)
-> {"admitted": {id: form}, "log": {id: {"disposition",
"reason"}}}) and runs it over the 16 crossings in
crossings.json. Admitted forms are re-validated against
their contracts by the lesson's own machinery
(../solution/boundary.py -- the contracts are the shared
ground truth; they are not yours to edit).

The bars (from the lesson, stated before any code):

  safety      ZERO invalid admissions. Every admitted
              form must satisfy its contract on
              re-validation -- downstream code reads
              what the gate admits, and it trusts it.
  yield       at least 7 of the 8 legitimate crossings
              (gold admit or repair) admitted in valid
              form. Refusal and quarantine are legitimate
              for the other eight -- and priced here.
  accounting  EVERY crossing carries a named disposition
              with a non-empty reason, and at least 3
              crossings are held in quarantine. Nothing
              vanishes silently in either direction:
              neither admitted without a word nor dropped
              without one.

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

import boundary  # noqa: E402  (the shared contracts)

DOC = json.load(open(os.path.join(HERE, "crossings.json")))
CROSSINGS = DOC["crossings"]
LEGIT = [c for c in CROSSINGS
         if c["gold"]["disposition"] in ("admit", "repair")]
YIELD_BAR = 7
QUARANTINE_BAR = 3


def load_gate(path):
    spec = importlib.util.spec_from_file_location(
        "gate_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_gate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", default=None,
                        help="gate module to grade (default: "
                             "the worked solution in solution/)")
    args = parser.parse_args()
    path = args.gate or os.path.join(HERE, "solution", "admit.py")
    run_gate = load_gate(path)

    print("gate under test: {}".format(path))
    result = run_gate(CROSSINGS)
    admitted = result.get("admitted", {})
    log = result.get("log", {})

    by_id = {c["id"]: c for c in CROSSINGS}
    invalid = [cid for cid, form in admitted.items()
               if not boundary.form_valid(by_id[cid], form)]
    yielded = [c["id"] for c in LEGIT
               if c["id"] in admitted
               and boundary.form_valid(c, admitted[c["id"]])]
    unaccounted = [c["id"] for c in CROSSINGS
                   if c["id"] not in log
                   or log[c["id"]].get("disposition")
                   not in boundary.DISPOSITIONS
                   or not (log[c["id"]].get("reason") or "")
                   .strip()]
    held = [cid for cid, entry in log.items()
            if entry.get("disposition") == "quarantine"]

    print("{:6s} {:10s} {:10s} {}".format(
        "id", "gold", "gate", "outcome"))
    for c in CROSSINGS:
        entry = log.get(c["id"], {})
        disp = entry.get("disposition", "--")
        if c["id"] in invalid:
            out = "INVALID ADMITTED"
        elif disp == c["gold"]["disposition"]:
            out = "as gold"
        elif c["id"] in yielded:
            out = "admitted in valid form"
        else:
            out = "differs from gold"
        print("{:6s} {:10s} {:10s} {}".format(
            c["id"], c["gold"]["disposition"], disp, out))
    print()
    rows = [
        ("safety", "no invalid admissions",
         not invalid,
         "{} invalid".format(len(invalid))),
        ("yield",
         "legitimate admitted valid >= {} of {}".format(
             YIELD_BAR, len(LEGIT)),
         len(yielded) >= YIELD_BAR,
         "{} admitted valid".format(len(yielded))),
        ("accounting",
         "every crossing named, >= {} held".format(QUARANTINE_BAR),
         not unaccounted and len(held) >= QUARANTINE_BAR,
         "{} unaccounted, {} held".format(
             len(unaccounted), len(held))),
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
          "legitimate crossed, everything is accounted "
          "for.".format(len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
