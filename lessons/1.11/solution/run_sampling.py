#!/usr/bin/env python3
"""Lesson 1.07 -- Temperature & Sampling.

    python3 run_sampling.py             run every section
    python3 run_sampling.py softmax     one distribution, five temperatures
    python3 run_sampling.py sweep       variance per setting, three tasks
    python3 run_sampling.py filters     top-k and top-p, measured
    python3 run_sampling.py voting      majority votes vs the greedy line
    python3 run_sampling.py settings    the shipped policy vs the default

WHY THIS LESSON EXISTS. Every stand-in in this course has been
deterministic -- same input in, same answer out -- and 1.06
closed by naming that as a choice. A production model holds a
distribution over what it might say and SAMPLES from it under
controls the caller sets: temperature, candidate filters, and
the number of draws. Those controls are almost never set on
purpose; the provider default (temperature 1, no filters, one
draw) is inherited by accident and then blamed on the model.
This lesson measures what the dials do on the Assistant's own
three task families and ships a defended setting per family:
sampling@1.0.0 in sampling.py.

THE LAB. Draws come from sampling_lab, a small documented
simulator of the sampling step itself: fixed per-case logits
(the model's judgement, printed in tasks.json), the textbook
softmax over logit / T, top-k / top-p truncation, and seeded
draws so every number here reproduces exactly. The lab is crude
the way a labelled diagram is crude; what it measures is the
settings, and the settings are the part you control.

SECTIONS
  1. softmax  -- one case's distribution at five temperatures,
                 with its entropy: the dial, drawn and computed.
  2. sweep    -- per task, per temperature: extraction accuracy
                 and self-agreement; grading exact match and
                 mean absolute error; brainstorming diversity,
                 concentration and off-brief tail draws.
  3. filters  -- at temperature 1: no filter, top-k 2, top-p
                 0.9 -- what each cut buys and what it costs.
  4. voting   -- majority-of-k at temperature 0.7 against the
                 greedy line, priced per filed answer on atlas.
  5. settings -- the shipped policy beside the inherited
                 default, headline metrics and price.

Standard library only. Run it; argue with it; then do the
exercise, which grades YOUR settings on the same suites.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sampling
import sampling_lab
from inbox_client import PROVIDERS
from tokenizer import count_tokens

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = json.load(open(os.path.join(HERE, "tasks.json")))

ATLAS_IN = PROVIDERS["atlas"]["price_in_per_mtok"]
ATLAS_OUT = PROVIDERS["atlas"]["price_out_per_mtok"]

TEMPERATURES = (0.0, 0.3, 0.7, 1.0, 1.5)

# Representative prompts, counted with the pack's BPE counter --
# the price of a draw is the price of the call that carries it.
PROMPTS = {
    "extraction": ("File the email under exactly one label: "
                   "action, reply, fyi, archive. Email: "),
    "grading": ("Score the drafted reply from 1 to 5 against "
                "the rubric. Draft: "),
    "brainstorming": ("Suggest a subject line for this send. "),
}


def price_per_draw(task, case):
    """One sampled call on atlas: the counted prompt in, the
    counted candidate out."""
    prompt = PROMPTS[task] + case["gist"]
    in_tok = count_tokens(prompt)
    out_tok = max(1, round(sum(count_tokens(c["text"])
                               for c in case["candidates"])
                           / len(case["candidates"])))
    return in_tok * ATLAS_IN / 1e6 + out_tok * ATLAS_OUT / 1e6


def _setting(temperature, top_k=None, top_p=None, vote_k=1):
    return {"temperature": temperature, "top_k": top_k,
            "top_p": top_p, "vote_k": vote_k}


def section_softmax():
    print("=" * 72)
    print("1. SOFTMAX -- one distribution, five temperatures")
    print("=" * 72)
    case = TASKS["extraction"][0]
    print("case {}: {}".format(case["id"], case["gist"]))
    print("the model's logits (its judgement, before any dial):")
    for cand in case["candidates"]:
        print("    {:8s} logit {:+.1f}".format(cand["text"],
                                               cand["logit"]))
    print()
    print("{:>6s}  {:>28s}  {:>8s}".format("T", "probabilities", "entropy"))
    for temp in (0.0, 0.25, 0.5, 1.0, 2.0):
        probs = sampling_lab.softmax(
            [c["logit"] for c in case["candidates"]], temp)
        row = "  ".join("{} {:.3f}".format(c["text"], p)
                        for c, p in zip(case["candidates"], probs))
        entropy = sampling_lab.entropy_bits(probs)
        print("{:>6.2f}  {:>28s}  {:>7.2f} bits".format(
            temp, row, entropy if entropy > 0 else 0.0))
    print()
    print("Temperature divides the logits before the softmax:")
    print("below 1 the gaps widen, above 1 they shrink, and 0 is")
    print("the limiting case -- greedy, the argmax every time. The")
    print("distribution's entropy is the dial's read-out: 0 bits")
    print("is a decision, 2 bits (four candidates) is a coin toss.")


def section_sweep():
    print("=" * 72)
    print("2. SWEEP -- output variance per setting, on the Assistant's tasks")
    print("=" * 72)
    print("200 seeded draws per case (brainstorming: 300 per prompt).")
    print("Per-draw metrics grade single draws; agreement is the")
    print("share of draws landing on each case's modal candidate.")
    print()
    print("{:>5s} | {:>22s} | {:>22s} | {:>26s}".format(
        "T", "extraction (12 cases)", "grading (10 cases)",
        "brainstorming (3 prompts)"))
    print("{:>5s} | {:>10s} {:>11s} | {:>10s} {:>11s} | {:>8s} {:>8s} {:>8s}"
          .format("", "accuracy", "agreement", "exact", "MAE",
                  "distinct", "top-1", "off/300"))
    for temp in TEMPERATURES:
        s = _setting(temp)
        ex = sampling.extraction_metrics(TASKS["extraction"], s)
        gr = sampling.grading_metrics(TASKS["grading"], s)
        br = sampling.brainstorming_metrics(TASKS["brainstorming"], s)
        print("{:>5.1f} | {:>10.3f} {:>11.3f} | {:>10.3f} {:>11.3f} | "
              "{:>8.1f} {:>8.3f} {:>8.1f}".format(
                  temp, ex["per_draw_accuracy"], ex["agreement"],
                  gr["per_draw_exact"], gr["per_draw_mae"],
                  br["distinct"], br["top_share"], br["offbrief_per_n"]))
    print()
    print("Read the columns as three different products. Extraction")
    print("and grading sell the SAME answer every time: from 0.3 up,")
    print("every step of temperature spends accuracy and agreement")
    print("and buys nothing the task can use. (The small rise at")
    print("0.3 -- 0.930 over greedy's 0.917 -- is one case's luck:")
    print("ex-07's argmax is the WRONG label, so single draws at a")
    print("little temperature sometimes land on the gold by chance.")
    print("The filed answer at 0.3 is still 0.917; luck is not a")
    print("setting.) Brainstorming sells variety: greedy repeats")
    print("one line forever (distinct 1.0), and diversity only")
    print("arrives with temperature -- trailing an off-brief tail.")


def section_filters():
    print("=" * 72)
    print("3. FILTERS -- the tail, cut before the draw (all at T = 1.0)")
    print("=" * 72)
    print("{:>10s} | {:>22s} | {:>26s}".format(
        "filter", "extraction accuracy", "brainstorming distinct / off"))
    for name, s in (("none", _setting(1.0)),
                    ("top-k 2", _setting(1.0, top_k=2)),
                    ("top-p 0.9", _setting(1.0, top_p=0.9))):
        ex = sampling.extraction_metrics(TASKS["extraction"], s)
        br = sampling.brainstorming_metrics(TASKS["brainstorming"], s)
        print("{:>10s} | {:>22.3f} | {:>12.1f} / {:.1f} per 300".format(
            name, ex["per_draw_accuracy"], br["distinct"],
            br["offbrief_per_n"]))
    print()
    print("A filter cannot create accuracy -- top-p on extraction")
    print("still draws the runner-up label a quarter of the time.")
    print("What it creates is a floor under variety: on")
    print("brainstorming the nucleus keeps 8.7 of 12 lines in")
    print("rotation and the off-brief line is never drawn at all,")
    print("where the unfiltered tail deals it in once per 300.")


def section_voting():
    print("=" * 72)
    print("4. VOTING -- majority of k draws at T = 0.7, against greedy")
    print("=" * 72)
    print("Case metrics averaged over 50 replicas (a single vote")
    print("is itself a draw). Price: the counted atlas price of")
    print("the draws behind one filed answer.")
    print()
    greedy_ex = sampling.extraction_case_metrics(
        TASKS["extraction"], _setting(0.0), replicas=50)
    greedy_gr = sampling.grading_case_metrics(
        TASKS["grading"], _setting(0.0), replicas=50)
    print("greedy (T=0, 1 draw):   extraction {:.3f}   grading exact "
          "{:.3f}  MAE {:.3f}".format(greedy_ex["case_accuracy"],
                                      greedy_gr["case_exact"],
                                      greedy_gr["case_mae"]))
    for k in (1, 5, 9):
        s = _setting(0.7, vote_k=k)
        ex = sampling.extraction_case_metrics(TASKS["extraction"], s,
                                              replicas=50)
        gr = sampling.grading_case_metrics(TASKS["grading"], s,
                                           replicas=50)
        price_ex = sum(price_per_draw("extraction", c)
                       for c in TASKS["extraction"]) / len(TASKS["extraction"]) * k
        print("majority of {:d} (T=0.7): extraction {:.3f}   grading "
              "exact {:.3f}  MAE {:.3f}   extraction answer ${:.6f}"
              .format(k, ex["case_accuracy"], gr["case_exact"],
                      gr["case_mae"], price_ex))
    print()
    print("Voting buys back most of what temperature spends. At")
    print("nine votes it even edges past the greedy line on this")
    print("pack (0.950 against 0.917) -- and the whole edge is")
    print("ex-07, the nearly-tied case: the vote rescues it in 40%")
    print("of runs and files the wrong label, with a quorum, in")
    print("the other 60%. A rescue that works 40% of the time is")
    print("not a fix; it is a slower coin. And the coin costs five")
    print("to nine times the price of the draw it imitates. Where")
    print("a sampler can be set to zero, zero is free. Voting is")
    print("the tax where it cannot.")


def section_settings():
    print("=" * 72)
    print("5. SETTINGS -- sampling@1.0.0 beside the inherited default")
    print("=" * 72)
    shipped = sampling.score_settings(TASKS, sampling.SETTINGS)
    default = sampling.score_settings(TASKS, sampling.DEFAULT_SETTINGS)
    print("extraction (filed-answer accuracy / per-draw):")
    print("    shipped  T=0            {:.3f} / {:.3f}".format(
        shipped["extraction"]["case_accuracy"],
        shipped["extraction"]["per_draw_accuracy"]))
    print("    default  T=1, 1 draw    {:.3f} / {:.3f}".format(
        default["extraction"]["case_accuracy"],
        default["extraction"]["per_draw_accuracy"]))
    print("grading (filed exact / MAE):")
    print("    shipped  T=0            {:.3f} / {:.3f}".format(
        shipped["grading"]["case_exact"], shipped["grading"]["case_mae"]))
    print("    default  T=1, 1 draw    {:.3f} / {:.3f}".format(
        default["grading"]["case_exact"], default["grading"]["case_mae"]))
    print("brainstorming (distinct of 12 / off-brief per 300):")
    print("    shipped  T=1, top-p .9  {:.1f} / {:.1f}".format(
        shipped["brainstorming"]["distinct"],
        shipped["brainstorming"]["offbrief_per_n"]))
    print("    default  T=1, no filter {:.1f} / {:.1f}".format(
        default["brainstorming"]["distinct"],
        default["brainstorming"]["offbrief_per_n"]))
    print()
    total = 0.0
    for task in ("extraction", "grading", "brainstorming"):
        s = sampling.SETTINGS[task]
        price = (sum(price_per_draw(task, c) for c in TASKS[task])
                 / len(TASKS[task]) * s.get("vote_k", 1))
        total += price
        print("price of one filed {} answer, shipped: ${:.6f}"
              .format(task, price))
    print("total, one answer per task: ${:.6f}".format(total))
    print("The default costs exactly the same per draw -- a")
    print("temperature is not a price dial. What the default")
    print("spends is not money; it is the accuracy above. The")
    print("only setting that costs money is vote_k (section 4).")
    print()
    print("Same model, same prompts, same pack. The only thing that")
    print("changed is who chose the settings -- the lesson, or the")
    print("default. That is the whole argument of 1.07.")


SECTIONS = {"softmax": section_softmax, "sweep": section_sweep,
            "filters": section_filters, "voting": section_voting,
            "settings": section_settings}


def main():
    names = sys.argv[1:] or list(SECTIONS)
    for name in names:
        SECTIONS[name]()
        print()


if __name__ == "__main__":
    main()
