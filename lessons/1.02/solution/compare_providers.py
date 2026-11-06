"""Act 3 driver: one question, three providers, three receipts.

Starts the three mock provider servers, asks the same question through
the same interface on each provider, and prints what each exchange
consumed: tokens, dollars, seconds. Then it sends the project brief to
the smallest provider to show the honest failure: a 400 that names
itself, converted by the client into ContextTooLargeError.

Run:  python3 compare_providers.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from inbox_client import ContextTooLargeError, ProviderClient
from providers_common import ProviderServers

QUESTION = [
    {"role": "system", "content": "You answer questions about an inbox."},
    {"role": "user", "content": "When does Project Aurora launch?"},
]


def main():
    with ProviderServers():
        print("same question, same interface, three providers")
        print(
            "provider  model     prompt  completion  cost (USD)   time (s)"
        )
        for name in ("sprout", "atlas", "oracle"):
            client = ProviderClient(name)
            answer = client.chat(QUESTION)
            usage = client.last_usage
            print(
                name.ljust(10)
                + client.model.ljust(10)
                + str(usage["prompt_tokens"]).rjust(6)
                + str(usage["completion_tokens"]).rjust(12)
                + ("%.7f" % client.last_cost_usd).rjust(13)
                + ("%.2f" % client.last_elapsed_s).rjust(9)
            )
            print("  answer: " + answer)

        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "project_brief.txt"), encoding="utf-8") as f:
            brief = f.read()
        big = [
            {"role": "system", "content": "You answer questions about a project brief."},
            {"role": "user", "content": "Summarise the following project brief.\n\n" + brief},
        ]
        print()
        print("now the brief (about 750 tokens) to sprout (limit 600):")
        try:
            ProviderClient("sprout").chat(big)
            print("  unexpected: sprout accepted the brief")
        except ContextTooLargeError as exc:
            print("  ContextTooLargeError: " + str(exc)[:150])


if __name__ == "__main__":
    main()
