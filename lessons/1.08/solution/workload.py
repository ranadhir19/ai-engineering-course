"""The six-task workload shared by the tutorial and the exercise.

Each task is a dict: an id, a kind, and the messages to send. Token
counts below are whitespace words across all message contents -- the
same counting the servers use, so the routing rule and the servers can
never disagree about a prompt's size.

    T1  ask     11 tokens     short inbox question
    T2  ask     15 tokens     short inbox question
    T3  summary 749 tokens    summarise the project brief (long output)
    T4  ask     300 tokens    question about the status memo
    T5  ask     14 tokens     short inbox question
    T6  analyse 758 tokens    question about the project brief
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def _messages(system, user):
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_workload():
    brief = _read("project_brief.txt")
    memo = _read("status_memo.txt")
    return [
        {
            "id": "T1",
            "kind": "ask",
            "messages": _messages(
                "You answer questions about an inbox.",
                "When does Project Aurora launch?",
            ),
        },
        {
            "id": "T2",
            "kind": "ask",
            "messages": _messages(
                "You answer questions about an inbox.",
                "What budget did Finance approve for the inbox assistant?",
            ),
        },
        {
            "id": "T3",
            "kind": "summary",
            "messages": _messages(
                "You summarise documents.",
                "Summarise the following project brief.\n\n" + brief,
            ),
        },
        {
            "id": "T4",
            "kind": "ask",
            "messages": _messages(
                "You answer questions about a status memo.",
                "According to the memo, what happens if the vendor review "
                "slips by two weeks?\n\n" + memo,
            ),
        },
        {
            "id": "T5",
            "kind": "ask",
            "messages": _messages(
                "You answer questions about an inbox.",
                "When was the design review meeting rescheduled to?",
            ),
        },
        {
            "id": "T6",
            "kind": "analyse",
            "messages": _messages(
                "You answer questions about a project brief.",
                "According to the brief, which workstream owns the "
                "evaluation harness?\n\n" + brief,
            ),
        },
    ]


def estimate_prompt_tokens(messages):
    """Whitespace-word count over all message contents (server parity)."""
    return sum(len(str(m.get("content", "")).split()) for m in messages)
