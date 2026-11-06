"""Exercise 1.06 -- the starter assembler.

This is the concatenator from the lesson, exactly as found in
the wild: the system text, then the examples, then the history,
then the documents, in the order the fields happen to be listed
-- and if the result is over budget, drop the oldest history
turns one at a time, then trim messages off the front until it
fits. Nothing is counted in advance and nothing is logged: the
report is empty.

It passes the two control scenarios and fails the other eight,
each failure a named disease from the lesson: a correction
outvoted by position, an instruction trimmed away, a needle
dropped with the oldest turn, a stale figure speaking last, and
-- under every failure -- items that left the window without a
word.

Your task: replace the policy, not the interface. Keep
``assemble(scenario) -> (messages, report)``; make every
scenario pass all four checks. The lesson's assembler in
../solution/context.py is one way; the harness does not care
whose policy it is, only what it survives.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "solution"))

from tokenizer import count_messages_tokens  # noqa: E402

SYSTEM_TEXT = (
    "You are the Inbox Assistant, answering questions about "
    "Project Aurora. Answer only from the context in this "
    "conversation. If the answer is not in the context, say: "
    "I don't know. Answer briefly, with the fact itself."
)


def assemble(scenario):
    messages = [{"role": "system", "content": SYSTEM_TEXT}]
    for example in scenario["examples"]:
        messages.append({"role": "user", "content":
                         "Worked example:\nQ: " + example["question"]
                         + "\nA: " + example["answer"]})
    first_history = len(messages)
    for turn in scenario["history"]:
        messages.append({"role": turn["role"], "content": turn["text"]})
    for doc in scenario["documents"]:
        messages.append({"role": "user", "content":
                         "Document: " + doc["name"] + "\n" + doc["text"]})
    messages.append({"role": "user", "content": scenario["question"]})
    budget = scenario["budget_tokens"]
    while (count_messages_tokens(messages) > budget
           and len(messages) > first_history + 1):
        messages.pop(first_history)
    while count_messages_tokens(messages) > budget and len(messages) > 1:
        messages.pop(0)
    return messages, {"items": []}
