"""Act 4 driver: fit the document set into atlas, two ways.

The naive way first: every document, whole, in pack order -- counted
locally (over budget for atlas once the answer's reserve is kept)
and actually sent to sprout, whose smaller window rejects it with
the named error. Then the policy way: fit_documents under a budget
of window minus reserve, sent through BudgetedProviderClient, which
counts before it sends. The loss log is printed in full: what was
kept, what was cut, and what each cut cost, in tokens.

Run:  python3 run_fitting.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from budget import BudgetedProviderClient, BudgetExceededError, fit_documents
from documents import doc_block, fixed_messages, load_documents, rank_documents
from inbox_client import ContextTooLargeError, ProviderClient
from providers_common import ProviderServers, request_count
from tokenizer import count_messages_tokens, count_tokens

PROVIDER = "atlas"
WINDOW = 4000
RESERVE = 400
BUDGET = WINDOW - RESERVE


def main():
    documents = load_documents()
    ranked = rank_documents(documents)
    print("document set (policy order = relevance to the question):")
    total = 0
    for doc in ranked:
        n = count_tokens(doc_block(doc["name"], doc["text"]))
        total += n
        print("  " + doc["name"].ljust(22) + str(n).rjust(5) + " tokens")
    fixed = count_messages_tokens(fixed_messages([]))
    print("  fixed parts (system + question): %d tokens" % fixed)
    print("  documents alone: %d tokens; budget for the whole prompt: %d (window %d - reserve %d)"
          % (total, BUDGET, WINDOW, RESERVE))
    print()

    naive = fixed_messages([doc_block(d["name"], d["text"]) for d in documents])
    print("NAIVE (all documents, whole, pack order): prompt counts %d tokens"
          % count_messages_tokens(naive))

    with ProviderServers():
        before = request_count("sprout")
        try:
            ProviderClient("sprout").chat(naive)
            print("  sprout accepted the naive prompt (unexpected)")
        except ContextTooLargeError as exc:
            print("  sent to sprout -> ContextTooLargeError in %d request: %s"
                  % (request_count("sprout") - before, str(exc)[:110]))
        budgeted = BudgetedProviderClient(PROVIDER, reserve_tokens=RESERVE)
        try:
            budgeted.chat(naive)
            print("  budgeted client sent the naive prompt (unexpected)")
        except BudgetExceededError as exc:
            print("  budgeted client refused it locally, 0 requests sent: %s" % str(exc)[:110])
        print()

        messages, losses = fit_documents(ranked, BUDGET)
        counted = count_messages_tokens(messages)
        print("FITTED (policy): prompt counts %d tokens (budget %d)" % (counted, BUDGET))
        for loss in losses:
            print("  LOSS %-22s %-9s kept %4d  dropped %4d"
                  % (loss["document"], loss["action"], loss["kept_tokens"], loss["dropped_tokens"]))
        if not losses:
            print("  LOSS none")
        answer = budgeted.chat(messages)
        print("  sent to %s: usage %s; cost $%.7f; %.2fs"
              % (PROVIDER, budgeted.last_usage, budgeted.last_cost_usd, budgeted.last_elapsed_s))
        print("  answer: " + answer[:150])


if __name__ == "__main__":
    main()
