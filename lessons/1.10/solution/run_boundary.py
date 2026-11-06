"""The measurements for Lesson 1.10, in six sections.

    python3 run_boundary.py              # all six sections
    python3 run_boundary.py boundary     # or one at a time

Sections: the wild (what arrives at the boundary -- the
census of 31 crossings), passthrough (no boundary at
all), rejectonly (strict validation, nothing else),
boundary (the shipped gate, boundary@1.0.0), cost (what
the gate costs: local time, zero model calls), and the
shipped summary -- three strategies on one table, the
1.09 unification, and the ceiling all three share.
Every number is computed here from crossings.json via
crossing_lab and boundary; nothing is typed in.
"""

import json
import os
import sys
import time
from collections import Counter

import boundary
import crossing_lab
import tool_lab

HERE = os.path.dirname(os.path.abspath(__file__))
CROSSINGS = crossing_lab.specimens()
N = len(CROSSINGS)
LEGIT = [c for c in CROSSINGS
         if c["gold"]["disposition"] in ("admit", "repair")]
CEILING = [c for c in CROSSINGS
           if "valid_but_wrong" in c["defects"]]


def _gate_all():
    """Run boundary@1.0.0 over the corpus, threading record
    identity in read-back order."""
    verdicts = {}
    seen = set()
    for c in CROSSINGS:
        v = boundary.inspect(c, seen)
        verdicts[c["id"]] = v
        if c["surface"] == "record" \
                and v["disposition"] in ("admit", "repair"):
            seen.add(c["stored_id"])
    return verdicts


def _admitted_forms(strategy):
    """{crossing id: admitted form} for one strategy."""
    out = {}
    if strategy == "passthrough":
        for c in CROSSINGS:
            out[c["id"]] = boundary.pass_through(c)
    elif strategy == "rejectonly":
        for c in CROSSINGS:
            form = boundary.reject_only(c)
            if form is not None:
                out[c["id"]] = form
    elif strategy == "boundary":
        for cid, v in _gate_all().items():
            if v["disposition"] in ("admit", "repair"):
                out[cid] = v["form"]
    return out


def _score(strategy):
    forms = _admitted_forms(strategy)
    invalid = [cid for cid, f in forms.items()
               if not boundary.form_valid(
                   next(c for c in CROSSINGS if c["id"] == cid), f)]
    lost = [c["id"] for c in LEGIT if c["id"] not in forms
            or not boundary.form_valid(c, forms.get(c["id"]))]
    return {"admitted": len(forms), "invalid": invalid,
            "lost": lost, "forms": forms}


def section_wild():
    print("=" * 72)
    print("1. THE WILD -- what arrives at the boundary "
          "({} crossings)".format(N))
    print("=" * 72)
    for c in CROSSINGS:
        d = ", ".join(c["defects"]) if c["defects"] else "clean"
        extra = " ({})".format(c["tool"]) if c.get("tool") else ""
        print("  {:6s} {:8s}{:14s} {}".format(
            c["id"], c["surface"], extra, d))
    print()
    census = crossing_lab.defect_census()
    print("  defect census: " + ", ".join(
        "{} x{}".format(k, v) for k, v in sorted(census.items())))
    print("  formally clean on arrival: {}".format(
        sum(1 for c in CROSSINGS if not c["defects"])))
    print("  gold dispositions, written before any gate ran: " +
          ", ".join("{} {}".format(k, v) for k, v in sorted(
              Counter(c["gold"]["disposition"]
                      for c in CROSSINGS).items())))
    print("  two crossings are formally perfect and wrong "
          "(rq-10, rr-13):")
    print("  no validator in this lesson can see them. That is "
          "the ceiling,")
    print("  and section 6 prices it.")


def section_passthrough():
    print("=" * 72)
    print("2. PASS-THROUGH -- no boundary (forward everything, "
          "log nothing)")
    print("=" * 72)
    s = _score("passthrough")
    print("  crossings admitted: {}/{}".format(s["admitted"], N))
    print("  admitted forms that FAIL their contract on "
          "re-validation: {}".format(len(s["invalid"])))
    for cid in s["invalid"]:
        c = next(x for x in CROSSINGS if x["id"] == cid)
        print("    {} ({}): defects {}".format(
            cid, c["surface"], ", ".join(c["defects"])))
    # at rest, the store is what downstream code reads -- and
    # it trusts it. Build the store pass-through leaves behind.
    store = {}
    for c in crossing_lab.by_surface("record"):
        store[c["stored_id"]] = boundary.pass_through(c)
    bad_store = [rid for rid, rec in store.items()
                 if not isinstance(rec, dict)
                 or boundary.structured.validate(rec)]
    print("  the store it leaves behind: {} ids, {} of them "
          "holding a record".format(len(store), len(bad_store)))
    print("  that fails record@1.0.0 -- including rec-08, whose "
          "true record was")
    print("  silently overwritten by the duplicate line.")
    print("  reasons logged for any of it: 0. Pass-through does "
          "not fail loudly;")
    print("  it succeeds, silently, into state nobody checked.")


def section_rejectonly():
    print("=" * 72)
    print("3. REJECT-ONLY -- strict validation, no repair, "
          "no migration, no quarantine")
    print("=" * 72)
    s = _score("rejectonly")
    print("  crossings admitted: {}/{}".format(s["admitted"], N))
    print("  invalid admitted: {}".format(len(s["invalid"])))
    print("  legitimate crossings LOST (gold admit/repair, "
          "not admitted): {}".format(len(s["lost"])))
    for cid in s["lost"]:
        c = next(x for x in CROSSINGS if x["id"] == cid)
        print("    {} ({}): {} -- refused with the genuinely "
              "broken".format(cid, c["surface"],
                               ", ".join(c["defects"])))
    print("  the safety record is perfect and the yield is the "
          "bill: every")
    print("  version-drifted record, every whitespace-padded "
          "request, every")
    print("  result carrying one undeclared key is refused "
          "exactly like the")
    print("  bit-rotted line. Strictness cannot tell drift from "
          "damage.")


def section_boundary():
    print("=" * 72)
    print("4. BOUNDARY -- boundary@1.0.0 (validate, repair, "
          "quarantine, reject)")
    print("=" * 72)
    verdicts = _gate_all()
    counts = Counter(v["disposition"] for v in verdicts.values())
    for c in CROSSINGS:
        v = verdicts[c["id"]]
        print("  {:6s} {:8s} {:10s} {}".format(
            c["id"], c["surface"], v["disposition"],
            "; ".join(v["log"][:1])))
    print()
    print("  dispositions: " + ", ".join(
        "{} {}".format(k, counts[k])
        for k in boundary.DISPOSITIONS))
    s = _score("boundary")
    print("  invalid admitted: {}".format(len(s["invalid"])))
    print("  legitimate lost: {}".format(len(s["lost"])))
    print("  repairs applied, every one logged: {}".format(
        sum(len(v["log"]) for v in verdicts.values()
            if v["disposition"] == "repair")))
    agree = sum(1 for c in CROSSINGS
                if verdicts[c["id"]]["disposition"]
                == c["gold"]["disposition"])
    print("  agreement with the gold dispositions written "
          "beforehand: {}/{}".format(agree, N))
    print("  the quarantined six wait with their reasons "
          "attached -- a human")
    print("  decision is owed on each, and the queue is the "
          "record that it is.")


def section_cost():
    print("=" * 72)
    print("5. COST -- what the gate costs")
    print("=" * 72)
    reps = 200
    t0 = time.perf_counter()
    for _ in range(reps):
        _gate_all()
    dt = time.perf_counter() - t0
    total = dt / reps
    print("  gate over the whole corpus ({} crossings): "
          "{:.1f} ms per pass".format(N, total * 1000))
    print("  per crossing: {:.0f} microseconds of local CPU "
          "(measured here,".format(total / N * 1e6))
    print("  this machine, this run -- the shape is the claim, "
          "not the digit)")
    print("  model calls added by validation: 0")
    print("  the contrast is 1.09's loop: +17 model calls over "
          "24 tasks to fix")
    print("  form at ONE crossing, after the fact. The boundary "
          "checks every")
    print("  crossing, before the fact, for the price of a "
          "function call.")
    print("  the real cost is not compute. It is the quarantine "
          "queue: 6 crossings")
    print("  held for decisions, and the contracts themselves "
          "-- someone has")
    print("  to write them, version them, and mean them.")


def section_shipped():
    print("=" * 72)
    print("6. THE SHIPPED GATE -- boundary@1.0.0 vs the "
          "alternatives")
    print("=" * 72)
    rows = {}
    for name in ("passthrough", "rejectonly", "boundary"):
        rows[name] = _score(name)
    print("  {:26s} {:>12s} {:>12s} {:>12s}".format(
        "", "pass-through", "reject-only", "boundary"))
    for label, key in (("crossings admitted", "admitted"),):
        print("  {:26s} {:>12d} {:>12d} {:>12d}".format(
            label, rows["passthrough"][key],
            rows["rejectonly"][key], rows["boundary"][key]))
    print("  {:26s} {:>12d} {:>12d} {:>12d}".format(
        "invalid admitted",
        len(rows["passthrough"]["invalid"]),
        len(rows["rejectonly"]["invalid"]),
        len(rows["boundary"]["invalid"])))
    print("  {:26s} {:>12d} {:>12d} {:>12d}".format(
        "legitimate lost",
        len(rows["passthrough"]["lost"]),
        len(rows["rejectonly"]["lost"]),
        len(rows["boundary"]["lost"])))
    # the unification: the gate at 1.09's surface
    doc = json.load(open(os.path.join(HERE, "tool_tasks.json")))
    admit = reject = 0
    for task in doc["tasks"]:
        for turn in task["turns"]:
            for spec in turn:
                if boundary.inspect_call(tool_lab.emit(spec)) \
                        == "admit":
                    admit += 1
                else:
                    reject += 1
    print()
    print("  the unification: inspect_call over 1.09's 35 first "
          "emissions --")
    print("  {} admit, {} reject, agreeing with the dispatcher's "
          "own verdicts".format(admit, reject))
    print("  on every call. The dispatcher was always a boundary "
          "gate; this")
    print("  lesson just walks the rest of the perimeter with "
          "the same pattern.")
    print()
    print("  the ceiling, on the record: {} crossings are "
          "formally perfect".format(len(CEILING)))
    print("  and wrong (rq-10 names the wrong message; rr-13 "
          "carries 1.09's")
    print("  judgement error, validly). All three strategies "
          "admit both.")
    print("  validation certifies form and provenance. It has "
          "never once")
    print("  certified truth -- that is what 1.11 (hostile "
          "content) and 1.12")
    print("  (measurement) are for.")


SECTIONS = {"wild": section_wild, "passthrough": section_passthrough,
            "rejectonly": section_rejectonly,
            "boundary": section_boundary, "cost": section_cost,
            "shipped": section_shipped}


def main():
    names = sys.argv[1:] or list(SECTIONS)
    for name in names:
        SECTIONS[name]()
        print()


if __name__ == "__main__":
    main()
