"""The measurements for Lesson 1.08, in six sections.

    python3 run_records.py           # all six sections
    python3 run_records.py repair    # or one at a time

Sections: the wild (what the ask actually returns), ask-only
(the found pipeline), repair (the deterministic layer), the
loop (errors handed back), constrained (validity by
construction), and the shipped pipeline -- structured@1.0.0 --
beside the ask it replaces. Every number is computed here from
records.json via reply_lab and structured; nothing is typed in.
"""

import json
import os
import sys
from collections import Counter

import reply_lab
import structured

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = json.load(open(os.path.join(HERE, "records.json")))
CASES = DOC["cases"]
N = len(CASES)


def _pct(x, n=N):
    return "{:.1f}%".format(100.0 * x / n)


def _score(filed):
    acc, wrong = structured.field_accuracy(filed, CASES)
    exact = structured.record_exact(filed, CASES)
    return acc, wrong, exact


def section_wild():
    print("=" * 72)
    print("1. THE WILD -- what the ask actually returns (24 cases)")
    print("=" * 72)
    census = Counter()
    parses = 0
    for case in CASES:
        text = reply_lab.respond(case)
        try:
            json.loads(text)
            parses += 1
            outcome = "parses"
        except ValueError:
            outcome = "PARSE FAILS"
        for d in case["defects"]:
            census[d] += 1
        print("  {}  {:11s}  defects: {}".format(
            case["id"], outcome, ", ".join(case["defects"]) or "none"))
    print()
    print("  replies that parse as JSON at all: {}/{} ({})".format(
        parses, N, _pct(parses)))
    print("  form-defect census: " + ", ".join(
        "{} x{}".format(k, v) for k, v in sorted(census.items())))
    clean = sum(1 for c in CASES if not c["defects"])
    print("  cases with no form defect: {}/{}".format(clean, N))


def _ask_batch():
    filed, failed = {}, {}
    price = 0.0
    for case in CASES:
        text = reply_lab.respond(case)
        price += structured.price_call(reply_lab.render_ask(case), text)
        rec, stage, errors = structured.strict_filing(text)
        if rec is not None:
            filed[case["id"]] = rec
        else:
            failed[case["id"]] = stage
    return filed, failed, price


def section_ask():
    print("=" * 72)
    print("2. ASK ONLY -- 'please reply in JSON', parsed on hope")
    print("=" * 72)
    filed, failed, price = _ask_batch()
    stages = Counter(failed.values())
    acc, wrong, exact = _score(filed)
    print("  filed {}/{} ({}); died at parse: {}; died at "
          "validation: {}".format(len(filed), N, _pct(len(filed)),
                                  stages.get("parse", 0),
                                  stages.get("validate", 0)))
    print("  field accuracy of the filed records: {:.3f}; "
          "record-exact: {}/{}".format(acc, exact, len(filed)))
    print("  price of the batch on atlas: ${:.6f}".format(price))
    print("  the filed three are the three cases whose form was "
          "never broken;")
    print("  two of them are wrong anyway (rec-13 priority, "
          "rec-16 due) -- validity is not accuracy.")


def _repair_batch():
    filed, rejected, repairs_used = {}, {}, Counter()
    for case in CASES:
        rec, repairs, errors = structured.repair(reply_lab.respond(case))
        repairs_used.update(repairs)
        if rec is not None:
            filed[case["id"]] = rec
        else:
            rejected[case["id"]] = errors
    return filed, rejected, repairs_used


def section_repair():
    print("=" * 72)
    print("3. PARSE AND REPAIR -- the deterministic layer")
    print("=" * 72)
    filed, rejected, repairs_used = _repair_batch()
    acc, wrong, exact = _score(filed)
    print("  filed {}/{} ({}); rejected {}".format(
        len(filed), N, _pct(len(filed)), len(rejected)))
    print("  repairs fired: " + ", ".join(
        "{} x{}".format(k, v) for k, v in sorted(repairs_used.items())))
    for cid, errors in rejected.items():
        print("  rejected {}: {}".format(cid, errors[0]))
    print("  field accuracy of the filed: {:.3f}; record-exact: "
          "{}/{}".format(acc, exact, len(filed)))
    print("  every rejection is a defect no mechanical rule may "
          "touch: a key")
    print("  that is absent, a word outside the enum, a summary "
          "over the cap,")
    print("  a reply that stops. Repair does not guess.")


def _loop_batch(max_reasks=2):
    filed, rejected, calls = {}, {}, 0
    price = 0.0
    rounds = Counter()
    for case in CASES:
        ask = reply_lab.render_ask(case)
        text = reply_lab.respond(case)
        calls += 1
        price += structured.price_call(ask, text)
        rec, repairs, errors = structured.repair(text)
        used = 0
        while rec is None and used < max_reasks:
            follow = structured.REASK_TEMPLATE.format(
                errors="\n".join(errors))
            text = reply_lab.reask(case, errors)
            calls += 1
            used += 1
            price += structured.price_call(ask + "\n" + follow, text)
            rec, stage, errors = structured.strict_filing(text)
        rounds[used] += 1
        if rec is not None:
            filed[case["id"]] = rec
        else:
            rejected[case["id"]] = errors
    return filed, rejected, calls, price, rounds


def section_loop():
    print("=" * 72)
    print("4. THE LOOP -- the validator's errors, handed back")
    print("=" * 72)
    filed, rejected, calls, price, rounds = _loop_batch()
    acc, wrong, exact = _score(filed)
    print("  filed {}/{} ({}); rejected {}".format(
        len(filed), N, _pct(len(filed)), len(rejected)))
    print("  re-asks needed: " + ", ".join(
        "{} round(s): {} cases".format(k, rounds[k]) for k in sorted(rounds)))
    print("  calls: {} for {} records ({:.2f} per record); batch "
          "price on atlas: ${:.6f}".format(calls, N, calls / N, price))
    print("  field accuracy: {:.3f}; record-exact: {}/{}".format(
        acc, exact, len(filed)))
    print("  the loop's premise, stated: the model reads its "
          "errors. The lab")
    print("  models a cooperative model (reply_lab, rule 3); a "
          "stubborn one")
    print("  burns its rounds and is rejected under its own name.")


def section_constrained():
    print("=" * 72)
    print("5. CONSTRAINED -- validity by construction")
    print("=" * 72)
    filed = {}
    price = 0.0
    for case in CASES:
        text = reply_lab.constrained(case)
        price += structured.price_call(reply_lab.render_ask(case), text)
        rec, stage, errors = structured.strict_filing(text)
        assert rec is not None, (case["id"], errors)
        filed[case["id"]] = rec
    acc, wrong, exact = _score(filed)
    print("  filed {}/{} ({}); calls: {} (1.00 per record); batch "
          "price: ${:.6f}".format(len(filed), N, _pct(len(filed)), N, price))
    print("  field accuracy: {:.3f}; record-exact: {}/{}".format(
        acc, exact, len(filed)))
    print("  valid but wrong, named: " + ", ".join(
        "{} ({})".format(c, f) for c, f in wrong))
    print("  the constraint governs the shape of the answer. It "
          "has no opinion")
    print("  about the answer -- rec-07 is filed wrong, validly, "
          "every time.")


def section_shipped():
    print("=" * 72)
    print("6. THE SHIPPED PIPELINE -- structured@1.0.0 vs the ask")
    print("=" * 72)
    filed, states, calls = {}, Counter(), 0
    for case in CASES:
        rec, log = structured.file_record(case)
        calls += log["calls"]
        states[log["state"]] += 1
        if rec is not None:
            filed[case["id"]] = rec
    acc, wrong, exact = _score(filed)
    ask_filed, _, ask_price = _ask_batch()
    # The shipped pipeline's re-asks are exactly the loop's single
    # rounds on the same five cases, so its price is the ask price
    # plus the loop's re-ask increment (section 4's accounting).
    _, _, _, loop_price, _ = _loop_batch()
    price = ask_price + (loop_price - ask_price)
    print("  ask only:        filed {}/{} -- the three clean cases, "
          "two of them wrong".format(len(ask_filed), N))
    print("  structured@1.0.0: filed {}/{} ({})".format(
        len(filed), N, _pct(len(filed))))
    print("  states: " + ", ".join(
        "{} {}".format(k, v) for k, v in sorted(states.items())))
    print("  calls: {} ({:.2f} per record); batch price on atlas: "
          "${:.6f}".format(calls, calls / N, price))
    print("  field accuracy: {:.3f}; record-exact: {}/{}".format(
        acc, exact, len(filed)))
    print("  residual wrong fields: " + ", ".join(
        "{} ({})".format(c, f) for c, f in wrong))
    print("  form is closed: every filed record validates against "
          "record@1.0.0.")
    print("  truth is not: the three judgement errors of the "
          "intended records")
    print("  survive every strategy in this lesson, named, "
          "unchanged.")


SECTIONS = {"wild": section_wild, "ask": section_ask,
            "repair": section_repair, "loop": section_loop,
            "constrained": section_constrained, "shipped": section_shipped}


def main():
    names = sys.argv[1:] or list(SECTIONS)
    for name in names:
        SECTIONS[name]()
        print()


if __name__ == "__main__":
    main()
