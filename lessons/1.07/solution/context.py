"""The context assembler: the window as a workspace you design.

Lesson AIE 1.06 -- Context Engineering.

1.05 engineered the prompt. But a prompt does not travel alone:
every real call carries instructions, worked examples, retrieved
documents and the conversation history, all competing for one
window at one price. Until this lesson the Assistant assembled
that crowd the way most systems do -- concatenation, in whatever
order the code happened to produce it, trimmed from wherever the
trimmer happened to cut. This module is the alternative: an
assembler with an explicit budget policy, in which every source
has a stated claim on the window, every exclusion is a decision,
and every decision is in the log.

The policy (POLICY_VERSION 1.0.0), in the order it is applied:

1. COUNT FIRST, WITH THE REAL METER (1.03). The budget is counted
   in BPE tokens by this pack's counter, and ``reserve_tokens``
   are held back for the answer -- a budget that forgets the
   reply is how windows get hit from the far side.

2. INSTRUCTIONS AND THE QUESTION ARE PINNED. They are seated
   first and never dropped, truncated or compacted. If they alone
   exceed the usable budget, BudgetExceededError is raised before
   anything is built -- the wall met in your own code (1.03).

3. EXAMPLES ARE CAPPED. Worked examples teach shape, not facts,
   so their claim is capped at EXAMPLE_CAP_FRACTION of the usable
   budget. Examples are included in order while they fit the cap;
   the rest are dropped, by id, in the log.

4. DOCUMENTS ARE RANKED, AND THE STRONGEST SPEAKS LAST.
   Selection walks documents in relevance order (the question's
   content words, counted -- 1.03's keyword overlap, generalised)
   and seats each whole while it fits; the strongest document
   that does not fit whole is seated as its longest whole-sentence
   prefix that fits, if at least MIN_USEFUL_TOKENS of room
   remain, and logged as truncated; the rest are dropped, logged.
   Emission reverses selection: weakest first, strongest last --
   because the reader (see context_lab) believes the last
   statement most, the best source gets the last word.

5. HISTORY IS COMPACTED, NEVER SILENTLY DROPPED. What remains of
   the budget belongs to the conversation. The newest turns are
   kept verbatim; every older turn is compacted by compact_turns:
   its durable sentences (the compactor's rules are printed
   there) are carried into a single "earlier in this conversation"
   block, seated before the verbatim turns. A turn whose sentences
   are all chatter contributes nothing and is logged as compacted
   with zero kept; a durable sentence that still does not fit is
   shed oldest-first and its turn is logged as dropped. Either
   way the turn is accounted for -- nothing leaves the window
   without a line in the log.

6. THE ORDER OF THE WINDOW. System (the pinned instructions) ->
   examples -> documents, weakest to strongest -> the compacted
   block -> verbatim history, oldest to newest -> the question.
   Reference material speaks before the live conversation, so a
   correction in the conversation overrides a stale document by
   position -- freshness by construction, not by hope.

The report is part of the return value, not a debug print: every
input item appears exactly once, with what was kept and what was
not. An exclusion you cannot name is a bug you have not met yet.

Standard library only.
"""

import re

from budget import BudgetExceededError, MIN_USEFUL_TOKENS
from tokenizer import count_messages_tokens, count_tokens

POLICY_VERSION = "1.0.0"

SYSTEM_TEXT = (
    "You are the Inbox Assistant, answering questions about "
    "Project Aurora. Answer only from the context in this "
    "conversation. If the answer is not in the context, say: "
    "I don't know. Answer briefly, with the fact itself."
)

EXAMPLE_CAP_FRACTION = 0.25

_STOPWORDS = {
    "what", "when", "which", "does", "the", "for", "and", "with",
    "about", "this", "that", "from", "into", "your", "please",
    "tell", "give",
}

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_VALUE = re.compile(
    r"(\b(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2}\b"
    r"|\b\d[\d,]*\s+dollars\b|\bRoom\s+\d[A-Za-z]?\b"
    r"|\b\d{1,2}\s*(?:am|pm)\b)")
_DURABLE_MARKERS = (
    "moved", "changed", "correction", "instead", "rule", "always",
    "never", "decided", "decision",
)

COMPACTED_HEADING = "Earlier in this conversation (compacted): "


def _content_words(text):
    return [w for w in re.findall(r"[a-z]+", text.lower())
            if len(w) > 3 and w not in _STOPWORDS]


def relevance_to(question, text):
    """How much ``text`` speaks to ``question``: occurrences of the
    question's content words. The 1.03 ranking rule, generalised
    from one fixed question to any question -- stated in the open,
    because a ranking rule you cannot read is a ranking you cannot
    argue with."""
    words = _content_words(question)
    low = text.lower()
    return sum(low.count(w) for w in words)


def _sentences(text):
    return [s for s in _SENTENCE_END.split(str(text).strip()) if s]


def _is_durable(sentence):
    """The compactor's rule for what survives compression. A
    sentence is durable if it states a value (a date, an amount,
    a room, a time) or carries a marker of decision or correction
    (moved, changed, correction, instead, rule, always, never,
    decided, decision). Everything else is chatter, for compaction
    purposes -- the rule is a heuristic and is printed here so its
    misses can be argued with."""
    if _VALUE.search(sentence):
        return True
    low = sentence.lower()
    return any(marker in low for marker in _DURABLE_MARKERS)


def compact_turns(turns):
    """Compact turns into their durable sentences.

    Returns (sentences, details): the kept sentences, in the
    turns' original order, and one detail per turn --
    {"id", "kept": [sentences], "dropped_sentences": n}."""
    sentences = []
    details = []
    for turn in turns:
        kept = [s for s in _sentences(turn["text"]) if _is_durable(s)]
        sentences.extend(kept)
        details.append({
            "id": turn["id"],
            "kept": kept,
            "dropped_sentences": len(_sentences(turn["text"])) - len(kept),
        })
    return sentences, details


def _doc_block(doc):
    return "Document: " + doc["name"] + "\n" + doc["text"].strip()


def _example_block(example):
    return ("Worked example:\nQ: " + example["question"]
            + "\nA: " + example["answer"])


def assemble(question, *, budget_tokens, examples=(), documents=(),
             history=(), reserve_tokens=64):
    """Assemble one call's context under an explicit budget policy.

    Returns (messages, report). ``budget_tokens`` is the caller's
    budget for the whole prompt, counted with this pack's BPE
    counter; ``reserve_tokens`` are held back inside it for the
    answer. Every input item is accounted for in
    report["items"], exactly once.
    """
    usable = budget_tokens - reserve_tokens
    system_message = {"role": "system", "content": SYSTEM_TEXT}
    question_message = {"role": "user", "content": question}
    pinned = count_messages_tokens([system_message, question_message])
    items = [{"item": "instructions", "source": "instructions",
              "action": "included", "kept_tokens": count_tokens(SYSTEM_TEXT),
              "dropped_tokens": 0}]
    if pinned > usable:
        raise BudgetExceededError("assembler", pinned, reserve_tokens,
                                  budget_tokens)
    remaining = usable - pinned

    # -- examples: capped claim, in order --
    example_messages = []
    cap = int(EXAMPLE_CAP_FRACTION * usable)
    spent = 0
    for example in examples:
        block = _example_block(example)
        tokens = count_tokens(block)
        if spent + tokens <= cap and tokens <= remaining:
            example_messages.append({"role": "user", "content": block})
            spent += tokens
            remaining -= tokens
            items.append({"item": example["id"], "source": "examples",
                          "action": "included", "kept_tokens": tokens,
                          "dropped_tokens": 0})
        else:
            items.append({"item": example["id"], "source": "examples",
                          "action": "dropped", "kept_tokens": 0,
                          "dropped_tokens": tokens})

    # -- documents: select strongest-first, emit weakest-first --
    ranked = sorted(documents,
                    key=lambda d: -relevance_to(question, d["text"]))
    chosen = []  # (doc, block, action) in selection order
    for doc in ranked:
        block = _doc_block(doc)
        tokens = count_tokens(block)
        if tokens <= remaining:
            chosen.append((doc, block, "included", tokens, tokens))
            remaining -= tokens
            continue
        kept_text = ""
        if remaining >= MIN_USEFUL_TOKENS:
            acc = []
            for sentence in _sentences(doc["text"]):
                trial = "Document: " + doc["name"] + "\n" + " ".join(acc + [sentence])
                if count_tokens(trial) > remaining:
                    break
                acc.append(sentence)
            if acc:
                kept_text = " ".join(acc)
        if kept_text:
            block = "Document: " + doc["name"] + "\n" + kept_text
            kept_tokens = count_tokens(block)
            chosen.append((doc, block, "truncated", tokens, kept_tokens))
            remaining -= kept_tokens
        else:
            items.append({"item": doc["id"], "source": "documents",
                          "action": "dropped", "kept_tokens": 0,
                          "dropped_tokens": tokens})
    document_messages = []
    for doc, block, action, full_tokens, kept_tokens in reversed(chosen):
        document_messages.append({"role": "user", "content": block})
        items.append({"item": doc["id"], "source": "documents",
                      "action": action, "kept_tokens": kept_tokens,
                      "dropped_tokens": full_tokens - kept_tokens})

    # -- history: compact the past, keep the recent verbatim --
    history_room = remaining
    verbatim = []          # turns, chronological
    compacted_ids = []     # turn details, chronological
    if history:
        sentences, details = compact_turns(history)
        detail_by_id = {d["id"]: d for d in details}
        # Promote newest turns to verbatim while the whole history
        # (verbatim + compacted block of the rest) fits the room.
        rest = list(history)
        while rest:
            turn = rest[-1]
            trial_verbatim = [turn] + verbatim
            trial_rest = rest[:-1]
            trial_sentences, _ = compact_turns(trial_rest)
            block = (COMPACTED_HEADING + " ".join(trial_sentences)
                     if trial_sentences else "")
            cost = (count_messages_tokens(
                        [{"role": t["role"], "content": t["text"]}
                         for t in trial_verbatim])
                    + (count_tokens(block) if block else 0))
            if cost <= history_room:
                verbatim = trial_verbatim
                rest = trial_rest
            else:
                break
        sentences, details = compact_turns(rest)
        # If even the compacted block does not fit, shed the oldest
        # turns' durable sentences until it does.
        while sentences:
            block = COMPACTED_HEADING + " ".join(sentences)
            if count_tokens(block) <= history_room - count_messages_tokens(
                    [{"role": t["role"], "content": t["text"]}
                     for t in verbatim]):
                break
            oldest = details[0]
            shed = len(oldest["kept"])
            sentences = sentences[shed:]
            details = details[1:]
            compacted_ids.append({"item": oldest["id"], "source": "history",
                                  "action": "dropped", "kept_tokens": 0,
                                  "dropped_tokens": count_tokens(
                                      next(t["text"] for t in history
                                           if t["id"] == oldest["id"]))})
        for detail in details:
            turn = next(t for t in history if t["id"] == detail["id"])
            turn_tokens = count_tokens(turn["text"])
            kept_tokens = count_tokens(" ".join(detail["kept"]))
            compacted_ids.append({"item": detail["id"], "source": "history",
                                  "action": "compacted",
                                  "kept_tokens": kept_tokens,
                                  "dropped_tokens": turn_tokens - kept_tokens})
        compacted_block = (COMPACTED_HEADING + " ".join(sentences)
                           if sentences else None)
    else:
        compacted_block = None
    items.extend(compacted_ids)
    for turn in verbatim:
        items.append({"item": turn["id"], "source": "history",
                      "action": "included",
                      "kept_tokens": count_tokens(turn["text"]),
                      "dropped_tokens": 0})
    items.append({"item": "question", "source": "question",
                  "action": "included",
                  "kept_tokens": count_tokens(question),
                  "dropped_tokens": 0})

    messages = [system_message]
    messages.extend(example_messages)
    messages.extend(document_messages)
    if compacted_block:
        messages.append({"role": "user", "content": compacted_block})
    for turn in verbatim:
        messages.append({"role": turn["role"], "content": turn["text"]})
    messages.append(question_message)

    total = count_messages_tokens(messages)
    report = {
        "policy": "context@" + POLICY_VERSION,
        "budget_tokens": budget_tokens,
        "reserve_tokens": reserve_tokens,
        "total_tokens": total,
        "headroom_tokens": budget_tokens - total,
        "items": items,
    }
    return messages, report
