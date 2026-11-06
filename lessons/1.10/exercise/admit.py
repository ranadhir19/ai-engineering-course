"""The found gate for Exercise 1.10 -- there isn't one.

This is the boundary as it exists wherever crossings are
consumed on arrival: whatever shows up is decoded if it
happens to parse and forwarded to the system as-is. A
drifted record is filed in its drifted form. A bit-rotted
line is filed as a string where a record belongs. An
over-cap request is acted on in full. Nothing is checked
and -- the part that makes it expensive -- nothing is
logged, so none of it is ever discovered by reading the
system's own records.

Your exercise is to replace it: a gate that gives every
crossing a named disposition (admit / repair /
quarantine / reject) with the reason attached, admits
nothing invalid, loses nothing legitimate, and holds
what only a decision can settle. The bars are in
README.md; the harness grades this module against them:

    python3 boundary_harness.py --gate admit.py

The interface is the contract: run_gate(crossings)
takes the crossings as data (the dicts from
crossings.json: id, surface, tool for results, and the
wild form under "wild") and returns a dict with:

- "admitted": {crossing id: the form admitted} -- for
  records, the record itself; for results and requests,
  the object the system will consume.
- "log": {crossing id: {"disposition": one of admit /
  repair / quarantine / reject, "reason": the located,
  named reason}} -- an entry for EVERY crossing,
  admitted or not.
"""

import json


def run_gate(crossings):
    """Pass-through, as a function: decode what parses,
    forward everything, log nothing."""
    admitted = {}
    log = {}
    for c in crossings:
        raw = c["wild"]
        if isinstance(raw, str):
            try:
                form = json.loads(raw)
            except ValueError:
                form = raw
        else:
            form = raw
        if c["surface"] == "record" and isinstance(form, dict):
            form = form.get("record", form)
        admitted[c["id"]] = form
        log[c["id"]] = {"disposition": "admit", "reason": ""}
    return {"admitted": admitted, "log": log}
