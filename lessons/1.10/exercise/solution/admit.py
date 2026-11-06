"""The worked solution for Exercise 1.10.

Built on the lesson's shipped machinery: boundary.py's
inspect() -- the same contracts, the same printed
migration tables, the same closed repair set the lesson
measures. Offline, there is no sender to correct a
crossing and no model to re-ask, so the gate's four
dispositions are the whole answer:

- admit what satisfies its contract as it stands;
- repair what mechanical, logged rules can settle
  (whitespace, an undeclared key, a versioned migration)
  and admit the repaired form;
- quarantine what is interpretable but not admissible
  -- over a cap, a value no version ever allowed, a
  result under the wrong contract -- held with its
  reason, visible, neither admitted nor dropped;
- reject what cannot be interpreted at all, by name.

One crossing (x-15) is admitted and wrong: formally
perfect, factually the 1.09 judgement error. The gate
says so in its reason, because that is all any gate can
honestly say about it.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "..", "..", "solution"))

import boundary  # noqa: E402

_CONTRACT = {"request": "request@1.0.0",
             "result": "result@1.0.0",
             "record": "record@1.0.0"}


def run_gate(crossings):
    admitted = {}
    log = {}
    seen = set()
    for c in crossings:
        v = boundary.inspect(c, seen)
        if c["surface"] == "record" \
                and v["disposition"] in ("admit", "repair"):
            seen.add(c["stored_id"])
        reason = "; ".join(v["log"])
        if not reason:
            reason = "valid as it stands under {}".format(
                _CONTRACT[c["surface"]])
        if "valid_but_wrong" in c["defects"]:
            reason += (" (formally perfect; its content is "
                       "wrong about the world -- no gate can "
                       "see that)")
        log[c["id"]] = {"disposition": v["disposition"],
                        "reason": reason}
        if v["disposition"] in ("admit", "repair"):
            admitted[c["id"]] = v["form"]
    return {"admitted": admitted, "log": log}
