"""Ask the inbox through one provider, chosen by configuration alone.

The provider is read from the INBOX_PROVIDER environment variable
(default "sprout"). No code changes between providers -- that is the
whole lesson in one file.

    INBOX_PROVIDER=atlas python3 ask_via.py

Assumes the three provider servers are running (compare_providers.py
and route_workload.py start their own; to run this file standalone,
start the servers first, one per terminal):

    python3 mock_provider_server.py --profile sprout
    python3 mock_provider_server.py --profile atlas
    python3 mock_provider_server.py --profile oracle
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from inbox_client import ProviderClient

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
