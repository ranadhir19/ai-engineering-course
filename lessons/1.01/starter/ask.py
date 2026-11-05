"""Starter driver: ask the mock server one question about the inbox.

Start the server first (in another terminal):
    python3 mock_model_server.py --port 8765 --mode ok
Then run:
    python3 ask.py

With the starter skeleton this fails with a NotImplementedError that
points at the TODO steps in inbox_client.py. That failure is intended:
implementing chat() is the lesson.
"""

from inbox_client import ModelClient


def main():
    client = ModelClient("http://127.0.0.1:8765")
    answer = client.chat([{"role": "user", "content": "When is the launch?"}])
    print(answer)


if __name__ == "__main__":
    main()
