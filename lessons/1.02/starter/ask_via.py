"""Ask the inbox through one provider, chosen by configuration alone.

The provider is read from the INBOX_PROVIDER environment variable
(default "sprout"). No code changes between providers -- that is the
whole lesson in one file.

    INBOX_PROVIDER=atlas python3 ask_via.py

In the starter this stops at the starting line until ProviderClient
exists (see the steps at the bottom of inbox_client.py). Assumes the
three provider servers are running; from the solution folder,
compare_providers.py and route_workload.py start their own.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from inbox_client import ProviderClient
except ImportError:
    print("STARTING LINE: ProviderClient is not built yet.")
    print("Work the four steps at the bottom of inbox_client.py,")
    print("then run this file again.")
    sys.exit(1)

QUESTION = [
    {"role": "system", "content": "You answer questions about an inbox."},
    {"role": "user", "content": "When does Project Aurora launch?"},
]


def main():
    name = os.environ.get("INBOX_PROVIDER", "sprout")
    client = ProviderClient(name)
    answer = client.chat(QUESTION)
    print("provider: " + name + " (" + client.model + ")")
    print("answer:   " + answer)
    print(
        "usage:    "
        + str(client.last_usage)
        + "  cost $"
        + ("%.7f" % client.last_cost_usd)
        + "  in "
        + ("%.2f" % client.last_elapsed_s)
        + "s"
    )


if __name__ == "__main__":
    main()
