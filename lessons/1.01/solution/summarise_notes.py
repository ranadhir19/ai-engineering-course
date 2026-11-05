"""Act 4 tutorial: summarise a notes file through the client.

Reads meeting_notes.txt (next to this file), sends it to the model as a
system + user message pair asking for a summary, and prints the result.

Start the server first (in another terminal):
    python3 mock_model_server.py --port 8765 --mode ok
Then run:
    python3 summarise_notes.py

Note what the mock does with this: it only ever answers from its inbox,
scoring by the words in your last user message -- which is exactly why
the summary it returns is extractive, and why later lessons add real
context handling.
"""

import os

from inbox_client import ModelClient


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "meeting_notes.txt"), "r", encoding="utf-8") as f:
        notes = f.read()
    client = ModelClient("http://127.0.0.1:8765")
    messages = [
        {
            "role": "system",
            "content": "You are a concise assistant. Summarise the user's notes in one or two sentences.",
        },
        {
            "role": "user",
            "content": "Summarise these meeting notes about the launch, the budget, and the rescheduled meeting:\n\n" + notes,
        },
    ]
    summary = client.chat(messages)
    print(summary)
    print("usage: " + str(client.last_usage))


if __name__ == "__main__":
    main()
