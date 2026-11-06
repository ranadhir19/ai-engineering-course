"""Lesson 1.07 -- the sampling policy: settings, defended per task.

    SETTINGS[task] = {"temperature": T, "top_k": k or None,
                      "top_p": p or None, "vote_k": draws or 1}

The build of this lesson is not code that samples -- sampling_lab
already does that, the way a provider does. The build is the
DECISION, measured: which setting each of the Assistant's task
families runs at, and what each choice costs and buys. The
measurements that defend these settings are reproduced by
run_sampling.py from the lab and tasks.json; the numbers below
are its output, not its input.

  extraction    temperature 0. Variance is pure loss when there
                is one right label: greedy files 11 of 12 cases
                (the twelfth, ex-07, is a case the model's own
                distribution gets wrong -- a judgement failure
                from 1.05's territory, and no temperature fixes
                a wrong argmax). Every degree of temperature
                above zero only deals some of those 11 away.
  grading       temperature 0. An audit cannot re-run last
                Tuesday's grade at a different score. Greedy:
                9 of 10 exact, mean absolute error 0.10 -- the
                one miss is gr-09, the polished draft whose
                distribution prefers the wrong score outright.
  brainstorming temperature 1.0, top_p 0.9. Variety is the
                product here, so the distribution runs as the
                model holds it -- but the nucleus cut removes
                the off-brief tail before the draw: the spammy
                line and the wrong-register line sit below the
                0.9 mass line and are never drawn, while the
                eleven on-brief lines keep their variety.

And the road not taken, priced in run_sampling.py: majority
voting at temperature 0.7 buys back most of the accuracy that
temperature spends (extraction filed answers: 0.817 at one
draw, 0.913 at five, 0.950 at nine) -- at five to nine times
the price. The nine-vote figure even edges past the greedy
0.917, and the whole edge is one case: ex-07, where the vote
rescues a nearly-tied distribution in 40% of runs and files
the wrong label, with a quorum, in the other 60%. A rescue
that works 40% of the time is not a fix; it is a slower coin.
Voting is the tax on a sampler you cannot set to zero. Where
you can set it to zero, set it to zero.

Standard library only.
"""

import sampling_lab

# sampling@1.0.0 -- one setting per task family, each defended
# by the sweep in run_sampling.py. vote_k > 1 means the answer
# is the majority of that many seeded draws.
SETTINGS = {
    "extraction": {"temperature": 0.0, "top_k": None,
                   "top_p": None, "vote_k": 1},
    "grading": {"temperature": 0.0, "top_k": None,
                "top_p": None, "vote_k": 1},
    "brainstorming": {"temperature": 1.0, "top_k": None,
                      "top_p": 0.9, "vote_k": 1},
}

# The provider default, as found -- what every task in this pack
# ran at before this lesson: one global temperature, no filters,
# one draw. The exercise starts here.
DEFAULT_SETTINGS = {
    task: {"temperature": 1.0, "top_k": None, "top_p": None,
           "vote_k": 1}
    for task in ("extraction", "grading", "brainstorming")
}


def setting_key(setting):
    """The canonical label of a setting -- part of the lab's
    seed formula, so identical settings draw identical numbers."""
    return "T={}:k={}:p={}:v={}".format(
        setting.get("temperature", 1.0), setting.get("top_k"),
        setting.get("top_p"), setting.get("vote_k", 1))


def draw_case(case, setting, n, replica=0):
    """n draws of one case under one setting (seeded)."""
    key = setting_key(setting) + ":r{}".format(replica)
    return sampling_lab.sample(
        case, setting.get("temperature", 1.0), n, key,
        top_k=setting.get("top_k"), top_p=setting.get("top_p"))


def answer_case(case, setting, replica=0):
    """The case's answer under a setting: the majority of
    vote_k draws (a single draw when vote_k == 1, the argmax
    when temperature == 0). Returns the candidate index."""
    draws = draw_case(case, setting, setting.get("vote_k", 1),
                      replica=replica)
    return sampling_lab.majority(draws)


def _gold_index(case):
    for i, cand in enumerate(case["candidates"]):
        if cand["text"] == case["gold"]:
            return i
    raise KeyError("gold not among candidates: " + case["id"])


def extraction_metrics(cases, setting, n=200):
    """Per-draw accuracy, per-case (majority) accuracy, and
    self-agreement: the mean share of draws landing on each
    case's modal candidate."""
    total, hits, agreement = 0, 0, 0.0
    case_hits = 0
    for case in cases:
        draws = draw_case(case, setting, n)
        gold = _gold_index(case)
        hits += sum(1 for d in draws if d == gold)
        total += n
        counts = {}
        for d in draws:
            counts[d] = counts.get(d, 0) + 1
        agreement += max(counts.values()) / n
        if answer_case(case, setting) == gold:
            case_hits += 1
    return {"per_draw_accuracy": hits / total,
            "case_accuracy": case_hits / len(cases),
            "agreement": agreement / len(cases)}


def grading_metrics(cases, setting, n=200):
    """Per-draw exact match and MAE against the gold score, and
    the same for the per-case (majority) answer."""
    total, exact, abs_err = 0, 0, 0.0
    case_exact, case_abs = 0, 0.0
    for case in cases:
        gold = int(case["gold"])
        draws = draw_case(case, setting, n)
        for d in draws:
            score = int(case["candidates"][d]["text"])
            exact += score == gold
            abs_err += abs(score - gold)
            total += 1
        answer = int(case["candidates"][answer_case(case, setting)]["text"])
        case_exact += answer == gold
        case_abs += abs(answer - gold)
    return {"per_draw_exact": exact / total,
            "per_draw_mae": abs_err / total,
            "case_exact": case_exact / len(cases),
            "case_mae": case_abs / len(cases)}


def brainstorming_metrics(cases, setting, n=300):
    """Diversity, concentration and tail risk, meaned over the
    prompts: distinct candidates drawn in n, the modal
    candidate's share, and off-brief draws per n."""
    distinct, top_share, offbrief = 0.0, 0.0, 0.0
    for case in cases:
        draws = draw_case(case, setting, n)
        counts = {}
        for d in draws:
            counts[d] = counts.get(d, 0) + 1
        distinct += len(counts)
        top_share += max(counts.values()) / n
        offbrief += sum(counts.get(i, 0) for i, cand
                        in enumerate(case["candidates"])
                        if cand.get("offbrief"))
    k = len(cases)
    return {"distinct": distinct / k,
            "top_share": top_share / k,
            "offbrief_per_n": offbrief / k}


def extraction_case_metrics(cases, setting, replicas=25):
    """Case accuracy of the FILED answer (the majority of
    vote_k draws), averaged over replicas -- a single replica's
    vote is itself a draw, and grading on one would grade luck.
    At temperature 0 every replica is identical by construction."""
    hits = 0
    for r in range(replicas):
        for case in cases:
            if answer_case(case, setting, replica=r) == _gold_index(case):
                hits += 1
    return {"case_accuracy": hits / (replicas * len(cases))}


def grading_case_metrics(cases, setting, replicas=25):
    """Case exact-match and MAE of the filed answer, averaged
    over replicas (see extraction_case_metrics)."""
    exact, abs_err = 0, 0.0
    for r in range(replicas):
        for case in cases:
            answer = int(case["candidates"][
                answer_case(case, setting, replica=r)]["text"])
            exact += answer == int(case["gold"])
            abs_err += abs(answer - int(case["gold"]))
    n = replicas * len(cases)
    return {"case_exact": exact / n, "case_mae": abs_err / n}


def score_settings(tasks, settings):
    """The headline table the exercise harness grades: one row
    per task family under one settings dict. Case metrics are
    replica-averaged; per-draw metrics describe single draws."""
    ex = extraction_metrics(tasks["extraction"], settings["extraction"])
    ex.update(extraction_case_metrics(tasks["extraction"],
                                      settings["extraction"]))
    gr = grading_metrics(tasks["grading"], settings["grading"])
    gr.update(grading_case_metrics(tasks["grading"], settings["grading"]))
    return {
        "extraction": ex,
        "grading": gr,
        "brainstorming": brainstorming_metrics(
            tasks["brainstorming"], settings["brainstorming"]),
    }
