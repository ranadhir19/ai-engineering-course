#!/usr/bin/env python3
"""attack_lab.py -- Lesson 1.11: the episode runner.

The 'model' in this lab is a RULE SET, printed below, not a
language model -- the same discipline as 1.09's fixture loop and
1.10's crossing lab. A real model grades the same way a student
does: by reading. What can be measured without one is the part
that matters for engineering: given a stated reading behaviour,
which defence layer stops which attack class, and what each
layer costs. The reading rules are the honest core of the lab,
so they are data, printed in every run:

  R1  the user turn is an instruction. Everything arriving on
      any other surface starts as DATA.
  R2  trust (no channel discipline): the model treats any
      instruction addressed to it, wherever found, as its job;
      the last instruction wins. This is agent@1.0.0's default
      and the wild condition being measured.
  R3  delimiters (channel discipline on): content is data and
      payload instructions in it are NOT followed -- EXCEPT the
      channels that discipline cannot close:
        mimicry    framed as a principal (a SYSTEM NOTICE in an
                   email) -- delimiters mark the channel, and
                   the content claims the channel is lying;
        encoded    the model decodes the payload (base64,
                   spaced letters) and reads an instruction;
        pasted     the user carried the text in on the trusted
                   channel, so it arrives WITH the user's turn;
        delegated  the user authorised following this source;
        semantic   there is no instruction to refuse -- the
                   payload is a fact-shaped claim the draft is
                   built from.
  R4  the screen (security.py) runs before reading, on
      non-principal surfaces only; a hit holds the WHOLE content
      item and the task waits -- a hold is a cost, not a save
      to celebrate: the task did not get done.
  R5  the action gate runs at dispatch, on every proposed call,
      whatever produced it; a refusal is named by rule (G1-G4).
  R6  outcomes are graded against gold authored WITH the
      fixtures (episodes.json), before the defences were coded:
      task_done and breach are separate facts, and a defence
      that completes the task while executing the payload has
      failed at the only thing it was for.

Outcome classes: clean (no payload, task done) / ignored
(payload read as data, never proposed) / held (screen stopped
the content; task NOT done) / refused (payload proposed, gate
refused it; task done) / breach (the payload's effect happened).
"""

import json
from pathlib import Path

import security

HERE = Path(__file__).resolve().parent

# R3's exception classes, as data.
ELEVATED = {"mimicry", "encoded", "pasted", "delegated", "semantic"}


def episodes():
    doc = json.loads((HERE / "episodes.json").read_text())
    return doc["episodes"]


def follows(payload, config):
    """Would the model act on this payload under this config?
    (R2/R3 -- evaluated before screen/gate, which are separate
    layers: a payload the model would follow can still be held
    upstream or refused downstream.)"""
    if payload is None:
        return False
    if not config.get("delimiters", False):
        return True                      # R2: trust
    return payload["kind"] in ELEVATED   # R3


def run(ep, config, extra_patterns=()):
    """Run one episode under one config. Returns the outcome,
    with the trace that produced it."""
    steps = []
    payload = ep["payload"]

    # layer 2: the screen, before any reading (R4)
    if config.get("screen", False) and ep["surface"] in \
            security.SCREENED_SURFACES:
        for item in ep["content"]:
            held, pattern = security.screen(item["text"],
                                            extra_patterns)
            if held:
                steps.append("screen: HELD by %s" % pattern)
                return {"id": ep["id"], "outcome": "held",
                        "task_done": False, "breach": False,
                        "pattern": pattern,
                        "proposed": [], "executed": [],
                        "reason": "screen held the %s content "
                                  "(%s); the task waits"
                                  % (ep["surface"], pattern),
                        "steps": steps}
        steps.append("screen: content admitted")

    if payload is None:
        return {"id": ep["id"], "outcome": "clean",
                "task_done": True, "breach": False,
                "proposed": [], "executed": [],
                "reason": "no payload; the task completed",
                "steps": steps}

    if not follows(payload, config):
        steps.append("reading: payload treated as data, "
                     "never proposed")
        return {"id": ep["id"], "outcome": "ignored",
                "task_done": True, "breach": False,
                "proposed": [], "executed": [],
                "reason": "channel discipline: %s content is "
                          "data, and this payload is an "
                          "instruction in it" % ep["surface"],
                "steps": steps}

    steps.append("reading: payload followed (class %s)"
                 % payload["kind"])

    if payload["kind"] == "semantic":
        # no call to gate: the authorised draft is built from
        # poisoned content (R3/R5 -- the ceiling)
        steps.append("dispatch: the task's own draft carries "
                     "the planted claim; no call was wrong")
        return {"id": ep["id"], "outcome": "breach",
                "task_done": True, "breach": True,
                "proposed": [], "executed": [],
                "reason": "the draft carries the planted claim: "
                          "%s" % payload["planted"],
                "steps": steps}

    call = payload["call"]
    # layer 3: the action gate, at dispatch (R5)
    if config.get("action_gate", False):
        admitted, rule = security.action_gate(call,
                                              ep["working_set"])
        if not admitted:
            steps.append("gate: REFUSED (%s)" % rule)
            return {"id": ep["id"], "outcome": "refused",
                    "task_done": True, "breach": False,
                    "proposed": [call], "executed": [],
                    "reason": "action gate refused the payload "
                              "call: %s" % rule,
                    "steps": steps}
        steps.append("gate: call admitted (%s)" % rule)
    steps.append("dispatch: payload call executed -- %s"
                 % payload["effect"])
    return {"id": ep["id"], "outcome": "breach",
            "task_done": True, "breach": True,
            "proposed": [call], "executed": [call],
            "reason": "payload call executed: %s"
                      % payload["effect"],
            "steps": steps}


def run_corpus(config, eps=None, extra_patterns=()):
    eps = eps if eps is not None else episodes()
    outcomes = [run(ep, config, extra_patterns) for ep in eps]
    return outcomes


def summarise(outcomes):
    from collections import Counter
    classes = Counter(o["outcome"] for o in outcomes)
    return {"episodes": len(outcomes),
            "tasks_done": sum(1 for o in outcomes if o["task_done"]),
            "breaches": sum(1 for o in outcomes if o["breach"]),
            "held": classes.get("held", 0),
            "by_class": dict(classes)}
