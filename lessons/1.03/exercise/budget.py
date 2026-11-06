"""The fitting policy for Lesson 1.03 (exercise starter).

The instruments are given: tokenizer.count_tokens counts a prompt
the way a real meter would, and BudgetedProviderClient (below)
refuses -- locally, before any request -- a prompt whose count plus
the reserve exceeds the window.

What no library can give you is the policy: **which documents earn
their place in a window that cannot hold them all, and what happens
to the ones that do not.** That policy is this exercise, and like
every policy in this course it is graded by a harness, not by taste.

Implement ``fit_documents`` under exactly the stated policy:

1. Walk the documents in the order given (the caller ranks them;
   use documents.rank_documents).
2. Include a document whole while the assembled prompt -- counted
   exactly, fixed parts included -- stays within the budget.
3. A document that does not fit whole: keep its longest
   whole-sentence prefix that fits, if the room remaining is at
   least MIN_USEFUL_TOKENS; otherwise skip it.
4. The system message and the question are never shed.
5. Return (messages, losses): one loss entry per document not
   included whole -- {"document", "action", "kept_tokens",
   "dropped_tokens"} -- with kept + dropped equal to the document
   block's full token count.

The starter below ignores ranking (it takes the documents in the
order given), never truncates, and logs no losses -- the honest
baseline the harness will show you.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "solution"))

from budget import BudgetExceededError, BudgetedProviderClient  # noqa: E402,F401
from documents import doc_block, fixed_messages  # noqa: E402
from tokenizer import count_messages_tokens  # noqa: E402

MIN_USEFUL_TOKENS = 120


def fit_documents(documents, budget_tokens):
    """Starter policy: pack order, whole-or-skip, no loss log."""
    blocks = []
    for doc in documents:
        block = doc_block(doc["name"], doc["text"])
        if count_messages_tokens(fixed_messages(blocks + [block])) <= budget_tokens:
            blocks.append(block)
    return fixed_messages(blocks), []
