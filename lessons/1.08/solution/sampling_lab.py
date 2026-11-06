"""The stand-in sampler for Lesson 1.07 -- a documented sampling lab.

Every stand-in in this course so far has been deterministic: same
input in, same answer out (that was 1.06's closing observation, and
this lesson is its examination). A production model is not like
that. Before it says anything, it holds a DISTRIBUTION over what
it might say next -- a score (a logit) for every candidate -- and
then it SAMPLES from that distribution under controls the caller
chooses: the temperature, the candidate filters (top-k, top-p),
and, one level up, how many samples to draw and how to combine
them. The prompt decides what the distribution is about; 1.05 and
1.06 engineered everything that shapes it. What the caller does
with the distribution afterwards is this lesson's subject, and it
is decided by dials most callers never touch.

This lab is a small, fully documented simulator of that last
step. Every rule below mirrors the real mechanism; the rules are
the contract, printed here so a reader can predict the lab the
way the lesson teaches you to predict a sampler: from its
specification.

The lab's rules:

1. THE DISTRIBUTION IS FIXED BEFORE THE DIALS. Each case in
   tasks.json carries the model's candidate completions with a
   logit for each -- its relative preference, before sampling.
   Those logits are the model's judgement, and no sampling
   setting can improve them: temperature reshapes the
   distribution, filters truncate it, voting aggregates draws
   from it. Sampling is not a quality dial. It is a VARIANCE
   dial, and variance is sometimes the product and sometimes
   the defect.

2. TEMPERATURE DIVIDES. The probability of candidate i is
   exp(logit_i / T) / sum_j exp(logit_j / T). T below 1 sharpens
   (differences grow); T = 1 is the distribution as the model
   holds it; T above 1 flattens (differences shrink). T = 0 is
   the limiting case and is implemented as what providers mean
   by it: greedy decoding -- the argmax, every time.

3. FILTERS CUT THE TAIL BEFORE THE DRAW. Top-k keeps the k
   highest-logit candidates; top-p (nucleus) keeps the smallest
   set of highest-probability candidates whose mass reaches p.
   What a filter removes can never be drawn; what it keeps is
   renormalised. Filters are how a caller buys variety without
   buying the tail.

4. DRAWS ARE SEEDED, SO MEASUREMENTS ARE EXACT. Every draw in
   this pack comes from random.Random with a printed seed
   formula ("1.07:<task>:<case>:<setting>:<replica>"), so a
   number measured today is the number measured tomorrow. A real
   provider's sampler is not reproducible run to run -- which is
   precisely why the lesson measures distributions (accuracy,
   agreement, diversity over hundreds of draws) and never
   anecdotes (one output, admired or deplored).

The tasks are the Assistant's own, one per family:

  extraction    -- 1.05's triage: file one email under one label.
                 One right answer per case; variance is pure loss.
  grading       -- score a drafted reply 1-5 against the rubric.
                 One defensible score per case; variance reads
                 as inconsistency to anyone audited by it.
  brainstorming -- subject lines for the Assistant's own sends.
                 Many right answers; variance IS the product --
                 and its tail contains the off-brief line.

Standard library only. No state: same case, setting and seed in,
same draws out.
"""

import math
import random

# The seed formula is part of the lab's contract (rule 4).
SEED_TEMPLATE = "1.07:{task}:{case}:{setting}:{replica}"


def softmax(logits, temperature):
    """The distribution over candidates at a temperature.

    temperature == 0 is greedy: a one-hot distribution on the
    argmax (ties broken toward the earliest candidate, as in the
    pack's other argmaxes). Otherwise the textbook softmax of
    logit / T, computed with the max subtracted for stability.
    """
    if temperature < 0:
        raise ValueError("temperature must be >= 0")
    if temperature == 0:
        top = max(range(len(logits)), key=lambda i: logits[i])
        return [1.0 if i == top else 0.0 for i in range(len(logits))]
    scaled = [x / temperature for x in logits]
    peak = max(scaled)
    exps = [math.exp(x - peak) for x in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def apply_filters(logits, probs, top_k=None, top_p=None):
    """Truncate a distribution (rule 3) and renormalise.

    Returns a new probability list, same length, zeros where a
    candidate was cut. top_k keeps the k largest logits; top_p
    keeps the smallest highest-probability set reaching p. When
    both are given, both cuts apply (the intersection survives).
    """
    keep = [True] * len(logits)
    if top_k is not None:
        ranked = sorted(range(len(logits)), key=lambda i: -logits[i])
        allowed = set(ranked[:top_k])
        keep = [i in allowed for i in range(len(logits))]
    if top_p is not None:
        ranked = sorted(range(len(logits)), key=lambda i: -probs[i])
        mass, nucleus = 0.0, set()
        for i in ranked:
            nucleus.add(i)
            mass += probs[i]
            if mass >= top_p:
                break
        keep = [keep[i] and i in nucleus for i in range(len(logits))]
    cut = [p if keep[i] else 0.0 for i, p in enumerate(probs)]
    total = sum(cut)
    if total <= 0:
        raise ValueError("filters removed the entire distribution")
    return [p / total for p in cut]


def distribution(case, temperature, top_k=None, top_p=None):
    """The effective distribution for one case under one setting."""
    logits = [c["logit"] for c in case["candidates"]]
    probs = softmax(logits, temperature)
    if top_k is not None or top_p is not None:
        probs = apply_filters(logits, probs, top_k=top_k, top_p=top_p)
    return probs


def _draw_index(probs, rng):
    r = rng.random()
    acc = 0.0
    for i, p in enumerate(probs):
        acc += p
        if r < acc:
            return i
    return len(probs) - 1


def sample(case, temperature, n, seed_key, top_k=None, top_p=None):
    """n seeded draws of one case under one setting.

    Returns the list of drawn candidate indices. seed_key is the
    setting label used in the lab's seed formula, so two runs of
    the same measurement draw the same numbers.
    """
    probs = distribution(case, temperature, top_k=top_k, top_p=top_p)
    rng = random.Random(SEED_TEMPLATE.format(
        task=case["task"], case=case["id"], setting=seed_key, replica=0))
    return [_draw_index(probs, rng) for _ in range(n)]


def entropy_bits(probs):
    """Shannon entropy of a distribution, in bits."""
    return -sum(p * math.log2(p) for p in probs if p > 0)


def majority(indices):
    """The modal draw (ties toward the most-drawn, then earliest)."""
    counts = {}
    for i in indices:
        counts[i] = counts.get(i, 0) + 1
    return max(sorted(counts), key=lambda i: counts[i])
