"""The stand-in model for Lesson 1.06 -- a deterministic context lab.

The providers from 1.02-1.05 answer from their own extractive rules;
they have nothing to say about *context*: what a model does with
the window it is handed. This lesson's subject is the window
itself, so its stand-in is a small, fully documented simulator of
how a production model treats an assembled context. Every rule
below mirrors a named, real behaviour; the rules are the contract,
printed here so a reader can predict the lab the way the lesson
teaches you to predict a model: from its specification.

The task the lab performs is the Assistant's new job: answer a
question about Project Aurora from the conversation it is given --
the instructions, the worked examples, the retrieved documents and
the history, assembled by somebody's policy (context.py is this
lesson's; the exercise grades yours).

The lab's rules:

1. FINDING BY RECENCY. It reads the context in the order it was
   assembled and answers from the LAST sentence that mentions the
   asked-about fact and carries a value of the asked kind (a date,
   an amount of money, a room, a time). Later statements override
   earlier ones -- the way production models overweight the recent
   and the repeated. It believes the context at face value,
   including a stale statement the assembler failed to retire:
   garbage placed last is gospel.

2. ABSTENTION IS AN INSTRUCTION, NOT A PERSONALITY TRAIT. If no
   sentence in the context carries the fact, the lab says
   "I don't know" ONLY when the standing instruction is present
   in the system message -- the first message -- telling it to
   answer only from the context and to say so when it cannot.
   If that instruction is absent (never sent, or truncated away
   by a careless assembler), the lab answers from its PRIORS:
   confident, plausible numbers it "just knows" -- printed below,
   each one stale in this pack's world. It never says it guessed.
   A model that hallucinates politely is not broken; it is
   uninstructed, which is the assembler's fault, not its own.

3. IT HAS NO OTHER KNOWLEDGE. A fact that is not in the context
   might as well not exist; a fact that is in the context is the
   whole truth. Everything the lab gets right or wrong was decided
   before the call -- by what the assembler included, in what
   order, at what price. That is the lesson: the call is the
   residue of the assembly.

PRIORS -- what the lab says when it answers from itself. Each is
the first version of the fact it ever heard, which is exactly how
stale priors behave in production:

    launch date   -> November 18   (the original announcement)
    rehearsal     -> November 12   (a date from an early draft)
    budget        -> 45000 dollars (the draft memo's figure)
    catering      -> 12000 dollars (a number from another event)
    design review -> Room 4B       (the room as first booked)

Standard library only. No state, no randomness: same context in,
same answer out -- which is what makes an assembly policy testable.
"""

import re

ABSTAIN = "I don't know"

PRIORS = {
    "launch": "November 18",
    "rehearsal": "November 12",
    "budget": "45000 dollars",
    "catering": "12000 dollars",
    "design review": "Room 4B",
}
DEFAULT_PRIOR = "November 18"

_MONTHS = ("January|February|March|April|May|June|July|August|"
           "September|October|November|December")
_VALUE_PATTERNS = {
    "date": re.compile(r"\b(?:" + _MONTHS + r")\s+\d{1,2}\b"),
    "money": re.compile(r"\b\d[\d,]*\s+dollars\b"),
    "room": re.compile(r"\bRoom\s+\d[A-Za-z]?\b"),
    "time": re.compile(r"\b\d{1,2}\s*(?:am|pm)\b"),
}

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _sentences(text):
    return [s.strip() for s in _SENTENCE_END.split(str(text).strip()) if s.strip()]


def _extract(sentence, value_kind):
    match = _VALUE_PATTERNS[value_kind].search(sentence)
    if not match:
        return None
    value = match.group(0)
    if value_kind == "money":
        value = value.replace(",", "")
    return value


def abstention_armed(messages):
    """True when the standing instruction survived assembly: the
    system (first) message tells the model to answer only from
    the context and to say "I don't know" when it cannot."""
    if not messages or messages[0].get("role") != "system":
        return False
    system = str(messages[0].get("content", ""))
    return "not in the context" in system and ABSTAIN in system


def answer(messages, key_phrases, value_kind):
    """The lab's answer: a value from the context, an abstention,
    or a prior -- decided entirely by what assembly put in front
    of it. ``key_phrases`` are the phrases a sentence must mention
    to count as being about the asked fact; ``value_kind`` is one
    of "date", "money", "room", "time"."""
    hits = []
    for message in messages:
        for sentence in _sentences(message.get("content", "")):
            low = sentence.lower()
            if any(phrase.lower() in low for phrase in key_phrases):
                hits.append(sentence)
    for sentence in reversed(hits):
        value = _extract(sentence, value_kind)
        if value is not None:
            return value
    if abstention_armed(messages):
        return ABSTAIN
    for phrase in key_phrases:
        for key, prior in PRIORS.items():
            if key in phrase.lower():
                return prior
    return DEFAULT_PRIOR
