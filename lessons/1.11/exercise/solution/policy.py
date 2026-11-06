#!/usr/bin/env python3
"""solution/policy.py -- the worked defence for Lesson 1.11.

security@1.0.0, unchanged from the lesson's shipped stack:
channel discipline + the boundary screen + the action gate.
No extra patterns: the exercise is calibrated so the shipped
stack, honestly accounted, meets all three bars -- the work
is in the accounting, not in new machinery.

account() names EVERY episode, in the harness's words, with
the reason the simulator recorded; and for the two episodes
that breach (ex-09, ex-10) the reason states the residual by
name. A defence that hides its ceiling fails this lesson even
when its numbers pass -- that rule is the lesson.
"""

CONFIG = {"delimiters": True, "screen": True, "action_gate": True}

EXTRA_PATTERNS = []

_WORD = {"held": "held", "refused": "refused", "ignored": "ignored",
         "clean": "clean"}


def account(ep, outcome):
    if outcome["outcome"] == "breach":
        word = "followed" if outcome["executed"] else "planted"
        return (word,
                "RESIDUAL -- %s. %s"
                % ((ep["payload"] or {}).get("kind", "content"),
                   ep["gold_note"]))
    return (_WORD[outcome["outcome"]], outcome["reason"])
