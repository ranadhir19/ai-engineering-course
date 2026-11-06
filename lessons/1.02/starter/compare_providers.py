"""Act 3 driver (STARTER): one question, three providers.

This is the starting line, not a bug: the driver needs ProviderClient,
which does not exist in the starter's inbox_client.py yet. Your Act 3
steps (listed at the bottom of inbox_client.py) build it: the
PROVIDERS table, cost_usd, and the ProviderClient subclass. When they
exist, this file runs unchanged and prints the three receipts side by
side. The worked build is in ../solution/.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from inbox_client import ContextTooLargeError, ProviderClient
except ImportError:
    print("STARTING LINE: ProviderClient is not built yet.")
    print("Work the four steps at the bottom of inbox_client.py,")
    print("then run this file again.")
    sys.exit(1)

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
