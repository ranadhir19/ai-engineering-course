#!/usr/bin/env python3
"""policy.py -- the defence you FOUND in this folder.

Channel discipline alone: content is data, and the plainly
instruction-shaped payloads in data are never followed. It
feels like the lesson's answer -- delimiters are what every
framework reaches for first.

Run it and look at what it does NOT do. It has no screen, so
anything that reaches the model AS an instruction executes:
mimicry (framed as a principal), the encoded tail (decoded,
then read), and both pastes (carried in on the trusted
channel). It has no action gate, so nothing downstream refuses
a proposed call. And its accounting is the accounting of a
system that only notices damage: account() below returns an
entry only when a payload call actually executed. The other
ten episodes pass in silence -- the semantic residual (ex-10)
among them; the delegated one (ex-09) is logged, but as a
bare execution, its residual nature nowhere stated.

The harness grades outcomes, not intentions: policies cannot
self-report, and account() is checked against the simulation.
Your job: rebuild this into a defence that meets all three
bars, and says so in reasons a principal can audit.
"""

# channel discipline only (../solution/security.py, CONFIGS)
CONFIG = {"delimiters": True, "screen": False, "action_gate": False}

EXTRA_PATTERNS = []


def account(ep, outcome):
    """The found defence's log: an entry exists only where a
    payload call executed. Everything else is silence."""
    if outcome["executed"]:
        return ("followed",
                "payload call executed: %s"
                % (ep["payload"] or {}).get("effect", ""))
    return None
