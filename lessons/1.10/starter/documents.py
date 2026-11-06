"""The document set for the 1.03 fitting task.

Five project documents, one question. The question is about launch
risks and their owners; the documents differ in how much of the
question they actually speak to, and together they are larger than
the window they must fit into -- which is the whole problem.

``relevance`` scores a document against the question the simple,
auditable way: how often the question's content words (and their
stated variants) occur in the document. It is the keyword-overlap
idea from 1.01's extractive answers, promoted to a ranking.
"""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

SYSTEM = "You answer questions about project documents."
QUESTION = "According to the documents, what are the launch risks, and who owns each one?"

# The question's content words, with the variants the policy counts.
# Stated in the open: a ranking rule you cannot read is a ranking
# you cannot argue with.
QUESTION_KEYWORDS = {
    "launch", "risk", "risks", "owner", "owners", "owns", "owned", "own",
}

DOCUMENT_FILES = [
    "launch_checklist.txt",
    "vendor_review.txt",
    "project_brief.txt",
    "support_digest.txt",
    "status_memo.txt",
]


def _read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def load_documents():
    """The set, in pack order: [{name, text}]."""
    return [{"name": name, "text": _read(name)} for name in DOCUMENT_FILES]


def relevance(text):
    """Occurrences of the question keywords in ``text``."""
    words = re.findall(r"[a-z]+", text.lower())
    return sum(1 for w in words if w in QUESTION_KEYWORDS)


def rank_documents(documents):
    """Documents in policy order: relevance descending; ties keep
    pack order (the sort is stable and the input is pack order)."""
    return sorted(documents, key=lambda d: -relevance(d["text"]))


def fixed_messages(doc_blocks):
    """The prompt shape the budgeter produces: the system message,
    then one user message carrying the question and the included
    document blocks."""
    user = QUESTION + "\n\n" + "\n\n".join(doc_blocks)
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]


def doc_block(name, text):
    return "Document: " + name + "\n" + text.strip()
