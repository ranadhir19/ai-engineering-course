#!/usr/bin/env python3
"""security.py -- Lesson 1.11: the shipped defence stack.

    version: security@1.0.0

1.10's boundary gate (boundary.py) certifies that whatever crosses
is well-formed and in-contract. It does not ask who WROTE the text
that produced the call. 1.11 asks exactly that. Three layers, in
the order an episode meets them:

  1. the channel discipline (in attack_lab.py: content arrives
     labelled by surface -- email, record, search, paste,
     delegation -- and only the user's own turn is an instruction
     channel; see attack_lab.FOLLOW)
  2. the boundary screen (this file): a deterministic pattern pass
     over content on NON-principal surfaces, the same engineering
     object as 1.10's validators -- regular expressions, no model,
     no judgement. A hit holds the content for a principal, the
     way 1.10 quarantined a crossing. What it screens for is FORM:
     a principal being impersonated (a SYSTEM NOTICE inside an
     email), an instruction addressed to the assistant inside
     data, an encoded run. It cannot screen for meaning, and it
     cannot tell a quotation from an order (ben-04 is its priced
     false positive).
  3. the action gate (this file): the 1.10 pattern moved to the
     dispatch point. A proposed call is admitted only if it stays
     inside the task's declared working set: its target must be a
     message the task is about, and a draft may quote only records
     in that set. Rules G1-G4, below. The gate refuses by name;
     it never edits a call into compliance.

What the stack does NOT do is also part of the spec, and the
corpus measures it: delegation transfers trust (a delegated
document's steps are followed, whoever edited them), and the
gate checks calls, not claims (a poisoned fact inside an
authorised draft crosses every layer). Those are atk-22, atk-23
and atk-24 -- the residuals, named in the shipped statement.

Pure standard library. A screen pass over the 30-episode corpus
costs microseconds per episode and no model calls; the real price
is the hold queue, priced in run_security.py.
"""

import re

VERSION = "security@1.0.0"

# ------------------------------------------------------------------
# layer 2: the boundary screen
# ------------------------------------------------------------------
# Each pattern is (name, regex). The names are printed on every
# hold so a principal reading the queue learns WHY, in one line --
# 1.10's named-disposition rule applied to content.
PATTERNS = [
    ("system-mimicry",
     r"\b(system|developer|platform)\s+(notice|note|message|"
     r"policy|update|alert)\b"),
    ("policy-claim",
     r"\bnew\s+(retention\s+)?policy\b|\bpolicy\s+update\b|"
     r"\beffective\s+immediately\b"),
    ("instruction-to-assistant",
     r"\bassistant\s*[:,\-]|\bnote\s+to\s+assistant\b|"
     r"\bto\s+assistant\b|\bassistants?\s+(should|must|shall)\b|"
     r"\bhave\s+your\s+assistant\b|\bnote\s+for\s+assistants?\b"),
    ("override-shape",
     r"\b(ignore|disregard|forget)\b[^.]{0,60}\b(instruction|"
     r"instructions|request|task|above|previous|user)\b"),
    ("mass-action-shape",
     r"\b(label|mark|file|draft|archive|send)\b[^.]{0,40}\b"
     r"(every|all)\b[^.]{0,30}\b(message|messages|inbox|email|"
     r"emails|record|records)\b"),
    ("encoded-run",
     r"[A-Za-z0-9+/]{40,}={0,2}"),
    ("spaced-run",
     r"(?:\b\w\s+){7,}\w\b"),
]

_COMPILED = [(name, re.compile(rx, re.IGNORECASE))
             for name, rx in PATTERNS]


def screen(text, extra_patterns=()):
    """Screen one content item. Returns (held, pattern_name).

    Deterministic: same text, same verdict, every run -- the
    property that makes it a gate and not a vibe. extra_patterns
    is how a policy (exercise) adds its own shapes to the shipped
    set without editing this file.
    """
    for name, rx in _COMPILED:
        if rx.search(text):
            return True, name
    for name, rx in extra_patterns:
        if re.search(rx, text, re.IGNORECASE):
            return True, name
    return False, None


# Surfaces whose content the screen guards. The user's own paste
# is deliberately NOT screened: the screen's job is impersonation
# and smuggling on channels the user did not write into; what the
# user carries in is the action gate's problem (and, when the user
# wrote it themselves, nobody's -- ben-05). A delegated document
# is not screened either: the user authorised following it, and
# screening it would refuse the delegation itself. Both gaps are
# measured, not hidden: atk-20/21 (paste) fall to layer 3 alone,
# and atk-22/23 (delegation) fall to nothing -- the residual.
SCREENED_SURFACES = {"email", "record", "search"}


# ------------------------------------------------------------------
# layer 3: the action gate
# ------------------------------------------------------------------
# G1  a write call's target message must be in the task's working
#     set (the messages the user's instruction is about).
# G2  a draft's quoted records must all be in the working set --
#     the draft is the exfiltration channel, so provenance is
#     checked on what the body carries, not just where it goes.
# G3  a wildcard target is in no working set, ever: "ALL" (and
#     "*") name the whole inbox, and no task is about the whole
#     inbox.
# G4  the gate refuses by name and returns the rule that fired;
#     it never rewrites a call into an admissible one (1.10's
#     dispatcher rule, kept).
WILDCARDS = {"ALL", "*", "all"}


def action_gate(call, working_set):
    """Returns (admitted, rule). working_set: the episode's
    declared set of message/record ids the task is about."""
    args = call.get("args", {})
    target = args.get("message_id")
    if target in WILDCARDS:
        return False, "G3 wildcard target"
    if target is not None and target not in working_set:
        return False, "G1 target outside the task's working set"
    for quoted in call.get("quotes", []):
        if quoted not in working_set:
            return False, ("G2 draft quotes %s, outside the "
                           "task's working set" % quoted)
    return True, "admitted"


# The three measured configurations, as data. The lesson runs
# all three over the same corpus; the exercise's policies speak
# the same shape.
CONFIGS = {
    # agent@1.0.0 as 1.09 left it: content read with full trust;
    # the 1.09/1.10 dispatchers still reject malformed calls --
    # every payload here is formally perfect, so they never fire.
    "trust": {"delimiters": False, "screen": False,
              "action_gate": False},
    # channel discipline alone: content is data; principal
    # framing, decoding, the user's own paste and authorised
    # delegation still reach the model as instructions.
    "delimiters": {"delimiters": True, "screen": False,
                   "action_gate": False},
    # the shipped stack: discipline + screen + action gate.
    "security@1.0.0": {"delimiters": True, "screen": True,
                       "action_gate": True},
}
