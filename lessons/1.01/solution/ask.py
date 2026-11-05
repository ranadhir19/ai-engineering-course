"""Solution driver: ask the mock server two questions about the inbox.

Start the server first (in another terminal):
    python3 mock_model_server.py --port 8765 --mode ok
Then run:
    python3 ask.py
"""

from inbox_client import ModelClient


def main():
    client = ModelClient("http://127.0.0.1:8765")
    questions = [
        "When is the launch?",
        "Has the budget been approved, and how much is it?",
    ]
    for question in questions:
        answer = client.chat([{"role": "user", "content": question}])
        print("Q: " + question)
        print("A: " + answer)
        print("usage: " + str(client.last_usage))
        print()


if __name__ == "__main__":
    main()
