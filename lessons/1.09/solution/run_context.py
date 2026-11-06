#!/usr/bin/env python3
"""Lesson 1.06 -- Context Engineering.

    python3 run_context.py             run every section
    python3 run_context.py anatomy     where one call's window goes
    python3 run_context.py scenarios   naive vs policy, ten problems
    python3 run_context.py compaction  what compaction keeps, measured
    python3 run_context.py cost        the window's price, both ways
    python3 run_context.py thread      the assembled window at work

WHY THIS LESSON EXISTS. 1.05 engineered the prompt. But the
prompt is one tenant of the window: every real call also carries
worked examples, retrieved documents and the conversation so
far, all competing for the same finite, priced space. Assembled
carelessly, the crowd fails in ways that look like model failures
-- the instruction trimmed away, the correction outvoted by the
document it corrected, the one fact that mattered dropped with
the oldest turn. This lesson measures those failures on this
pack's scenario set and builds the alternative: assemble() in
context.py, an explicit budget policy in which every source has
a stated claim, the strongest source speaks last, history is
compacted rather than silently dropped, and every exclusion is
in the log.

THE READER. Answers come from context_lab, a small deterministic
stand-in whose rules are printed in its docstring: it answers
from the last sentence that carries the fact, it abstains only
when the standing instruction survived assembly, and otherwise
it answers from stale priors, confidently. Every rule mirrors a
named production behaviour; the lab is crude the way a labelled
diagram is crude, and what it measures is the assembler, not a
model.

SECTIONS
  1. anatomy    -- the canonical thread assembly, counted per
                   source; the window's shape before its price.
  2. scenarios  -- the naive concatenator and the policy, run
                   over the ten-scenario pack, graded on four
                   checks per scenario: inside the budget, the
                   standing instruction present, the answer
                   right, and no silent drop.
  3. compaction -- what compaction kept and shed on the pack's
                   histories, measured in tokens and in facts.
  4. cost       -- the two assemblers' windows priced on atlas,
                   the pack's worked-example provider.
  5. thread     -- the emails of the running thread arrive as
                   documents over a conversation that corrects
                   two of them; the assembled window answers.

Standard library only. Run it; argue with it; then do the
exercise, which grades YOUR assembler on the same pack.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from context import SYSTEM_TEXT, assemble, compact_turns
from context_lab import answer as lab_answer
from inbox_client import PROVIDERS
from mock_provider_server import EMAILS
from tokenizer import count_messages_tokens, count_tokens

HERE = os.path.dirname(os.path.abspath(__file__))
SCENARIOS = json.load(open(os.path.join(HERE, "scenarios.json")))

ATLAS_IN = PROVIDERS["atlas"]["price_in_per_mtok"]

CANONICAL_QUESTION = "When does Project Aurora launch?"


# ----------------------------------------------------------------
# The naive assembler: concatenation and a trimmer -- the way
# most systems assemble context until the day it matters. It is
# written out in the open so its failures can be read, not rumoured.
# ----------------------------------------------------------------
def naive_assemble(scenario):
    """system + examples + history + documents (the order the
    fields happen to be listed in), nothing counted in advance;
    if the result is over budget, drop the oldest history turns
    one at a time; if it is STILL over budget, trim messages off
    the front until it fits. Nothing is logged: the report is
    empty, which is itself the point."""
    messages = [{"role": "system", "content": SYSTEM_TEXT}]
    for example in scenario["examples"]:
        messages.append({"role": "user", "content":
                         "Worked example:\nQ: " + example["question"]
                         + "\nA: " + example["answer"]})
    first_history = len(messages)
    for turn in scenario["history"]:
        messages.append({"role": turn["role"], "content": turn["text"]})
    for doc in scenario["documents"]:
        messages.append({"role": "user", "content":
                         "Document: " + doc["name"] + "\n" + doc["text"]})
    messages.append({"role": "user", "content": scenario["question"]})
    budget = scenario["budget_tokens"]
    while (count_messages_tokens(messages) > budget
           and len(messages) > first_history + 1):
        messages.pop(first_history)
    while count_messages_tokens(messages) > budget and len(messages) > 1:
        messages.pop(0)
    return messages, {"items": []}


def grade(messages, report, scenario):
    """The four checks, applied to either assembler."""
    checks = {}
    checks["budget"] = (count_messages_tokens(messages)
                        <= scenario["budget_tokens"])
    checks["instruction"] = (bool(messages)
                             and messages[0]["role"] == "system"
                             and "not in the context"
                             in messages[0]["content"])
    checks["answer"] = (lab_answer(messages, scenario["key_phrases"],
                                    scenario["value_kind"])
                        == scenario["gold"])
    accounted = {item["item"] for item in report.get("items", [])}
    present_ids = ({e["id"] for e in scenario["examples"]}
                   | {d["id"] for d in scenario["documents"]}
                   | {t["id"] for t in scenario["history"]})
    blob = "\n".join(m["content"] for m in messages)
    silent = [i for i in present_ids
              if i not in accounted
              and not _appears(messages, scenario, i, blob)]
    checks["no_silent_drop"] = not silent
    return checks


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


def policy_assemble(scenario):
    return assemble(scenario["question"],
                    budget_tokens=scenario["budget_tokens"],
                    examples=scenario["examples"],
                    documents=scenario["documents"],
                    history=scenario["history"])


# ----------------------------------------------------------------
def section_anatomy():
    scenario = next(s for s in SCENARIOS if s["id"] == "correction")
    messages, report = policy_assemble(scenario)
    print("=" * 72)
    print("1. ANATOMY -- where one assembled window goes")
    print("=" * 72)
    print("The canonical thread assembly: the correction scenario,")
    print("assembled by the policy at a %d-token budget."
          % scenario["budget_tokens"])
    print()
    by_source = {}
    for item in report["items"]:
        by_source[item["source"]] = (by_source.get(item["source"], 0)
                                     + item["kept_tokens"])
    total = report["total_tokens"]
    for source in ("instructions", "examples", "documents",
                   "history", "question"):
        if source in by_source:
            kept = by_source[source]
            print("  %-13s %5d tokens  (%4.1f%% of the window)"
                  % (source, kept, 100.0 * kept / total))
    print("  %-13s %5d tokens  (of the %d budget; headroom %d, "
          "of which %d is the answer reserve)"
          % ("TOTAL", total, scenario["budget_tokens"],
             scenario["budget_tokens"] - total,
             report["reserve_tokens"]))
    price = total / 1_000_000 * ATLAS_IN
    print()
    print("At atlas input pricing ($%.2f per million tokens) this "
          "window costs $%.6f." % (ATLAS_IN, price))
    print("The window is a workspace with four tenants and a rent.")
    print("The rest of the lesson is about eviction policy.")


# ----------------------------------------------------------------
def section_scenarios():
    print()
    print("=" * 72)
    print("2. SCENARIOS -- the concatenator vs the policy, ten problems")
    print("=" * 72)
    print("%-15s %-22s %-22s %s" % ("scenario", "naive", "policy",
                                    "gold"))
    naive_pass = policy_pass = 0
    for scenario in SCENARIOS:
        n_messages, n_report = naive_assemble(scenario)
        p_messages, p_report = policy_assemble(scenario)
        n_checks = grade(n_messages, n_report, scenario)
        p_checks = grade(p_messages, p_report, scenario)
        n_ok = all(n_checks.values())
        p_ok = all(p_checks.values())
        naive_pass += n_ok
        policy_pass += p_ok

        def mark(checks):
            if all(checks.values()):
                return "PASS"
            failed = [k for k, v in checks.items() if not v]
            return "fail: " + ",".join(failed)
        print("%-15s %-22s %-22s %s"
              % (scenario["id"], mark(n_checks), mark(p_checks),
                 scenario["gold"]))
    print()
    print("The naive concatenator passes %d of %d scenarios; the "
          "policy passes %d of %d."
          % (naive_pass, len(SCENARIOS), policy_pass, len(SCENARIOS)))
    print("Read the failures by family: position beats a stale")
    print("document only when the assembler orders for freshness;")
    print("pressure kills the instruction first when the trimmer")
    print("cuts from the front; and every naive failure drops")
    print("something without a word -- the log is the difference")
    print("between an eviction and a disappearance.")


# ----------------------------------------------------------------
def section_compaction():
    print()
    print("=" * 72)
    print("3. COMPACTION -- what the compressor keeps, measured")
    print("=" * 72)
    total_before = total_after = 0
    for scenario in SCENARIOS:
        if not scenario["history"]:
            continue
        sentences, details = compact_turns(scenario["history"])
        before = sum(count_tokens(t["text"])
                     for t in scenario["history"])
        after = count_tokens(" ".join(sentences))
        total_before += before
        total_after += after
        print("  %-15s history %4d -> compacted %4d tokens; "
              "%d durable sentences kept, %d shed"
              % (scenario["id"], before, after, len(sentences),
                 sum(d["dropped_sentences"] for d in details)))
    print()
    print("Across the pack: %d tokens of history compact to %d -- "
          "a %.0f%% reduction --"
          % (total_before, total_after,
             100.0 * (1 - total_after / total_before)))
    print("and the needle scenario shows what the percentage "
          "hides: the one")
    print("dated sentence in the oldest turn survives, which is "
          "the whole")
    print("difference between a summary and an answer.")


# ----------------------------------------------------------------
def section_cost():
    print()
    print("=" * 72)
    print("4. COST -- the window's price, both assemblers")
    print("=" * 72)
    n_total = p_total = 0
    for scenario in SCENARIOS:
        n_messages, _ = naive_assemble(scenario)
        p_messages, _ = policy_assemble(scenario)
        n_total += count_messages_tokens(n_messages)
        p_total += count_messages_tokens(p_messages)
    print("Across the ten scenarios, counted with the pack counter:")
    print("  naive windows : %5d tokens -> $%.6f on atlas"
          % (n_total, n_total / 1_000_000 * ATLAS_IN))
    print("  policy windows: %5d tokens -> $%.6f on atlas"
          % (p_total, p_total / 1_000_000 * ATLAS_IN))
    print()
    print("The policy is not cheaper by starvation -- it spends "
          "where the")
    print("answer lives and declines where it does not. The point "
          "of a")
    print("budget is not to spend less; it is to know what you "
          "bought.")


# ----------------------------------------------------------------
THREAD_HISTORY = [
    {"id": "t1", "role": "user",
     "text": "Please track Project Aurora across these emails for me."},
    {"id": "t2", "role": "assistant",
     "text": "Tracking Aurora: launch, budget and the design review."},
    {"id": "t3", "role": "user", "text":
     ("Correction from the team: the launch has moved. Project "
      "Aurora will launch on November 21, 2026.")},
    {"id": "t4", "role": "assistant",
     "text": "Launch updated to November 21."},
    {"id": "t5", "role": "user", "text":
     ("Also: the design review has moved to Room 2A. Same time, "
      "Thursday 2 pm.")},
    {"id": "t6", "role": "assistant",
     "text": "Design review moved to Room 2A -- noted."},
    {"id": "t7", "role": "user", "text":
     ("The coffee machine is rattling again, the parking lot was "
      "full this morning, and the plant in the break room is "
      "thriving. Office life continues.")},
]

THREAD_QUESTIONS = [
    ("When does Project Aurora launch?", ["will launch"], "date"),
    ("What is the budget for Project Aurora?", ["budget"], "money"),
    ("Which room is the design review in?", ["design review"], "room"),
]


def section_thread():
    print()
    print("=" * 72)
    print("5. THREAD -- the assembled window at work")
    print("=" * 72)
    documents = [{"id": "email-%d" % (i + 1),
                  "name": e["subject"],
                  "text": e["subject"] + "\n" + " ".join(e["sentences"])}
                 for i, e in enumerate(EMAILS)]
    print("The three emails of the running thread -- the mock "
          "server's own")
    print("table -- arrive as documents; the conversation has "
          "already")
    print("corrected two of them. Budget: 1400 tokens.")
    for question, keys, kind in THREAD_QUESTIONS:
        messages, report = assemble(
            question, budget_tokens=1400, documents=documents,
            history=THREAD_HISTORY)
        print("  Q: %-42s -> %s   (window: %d tokens)"
              % (question, lab_answer(messages, keys, kind),
                 report["total_tokens"]))
    print()
    print("Documents describe the world as announced; the "
          "conversation is")
    print("where the world gets corrected. An assembler that puts")
    print("documents last lets the announcement outvote the "
          "correction.")


SECTIONS = {"anatomy": section_anatomy, "scenarios": section_scenarios,
            "compaction": section_compaction, "cost": section_cost,
            "thread": section_thread}


def main(argv):
    names = argv[1:] or list(SECTIONS)
    for name in names:
        SECTIONS[name]()
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
