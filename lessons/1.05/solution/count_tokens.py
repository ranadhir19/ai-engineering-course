"""Act 3 driver: two meters on the same texts.

Trains (or loads) the pack tokenizer, then counts a shelf of real
artefacts from the course so far with both meters -- the whitespace
words the stand-in servers use, and the BPE tokens a real provider
would meter -- and prints the table the whiteboard predicted.

Run:  python3 count_tokens.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tokenizer import count_tokens, get_tokenizer, word_count
from workload import build_workload


def _row(label, text):
    words = word_count(text)
    tokens = count_tokens(text)
    print(
        "  "
        + label.ljust(38)
        + str(words).rjust(6)
        + " words"
        + str(tokens).rjust(6)
        + " tokens"
        + ("   %.2f tokens/word" % (tokens / words if words else 0))
    )
    return words, tokens


def main():
    tok = get_tokenizer()
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus.txt"),
              encoding="utf-8") as f:
        corpus = f.read()
    print("tokenizer: %d merges learned on a %d-byte corpus; vocabulary %d symbols"
          % (len(tok.merges), len(corpus.encode("utf-8")), tok.vocab_size))
    print("first merges learned: " + ", ".join(
        (a + b).decode("utf-8", "replace") for a, b in tok.merges[:8]))
    print()
    print("two meters, same texts:")
    tasks = {t["id"]: t for t in build_workload()}
    q = "When does Project Aurora launch?"
    _row("launch question (T1 user text)", q)
    t3 = " ".join(m["content"] for m in tasks["T3"]["messages"])
    _row("T3 prompt (summary of the brief)", t3)
    t4 = " ".join(m["content"] for m in tasks["T4"]["messages"])
    _row("T4 prompt (question + status memo)", t4)
    usage = json.dumps({"prompt_tokens": 749, "completion_tokens": 50, "total_tokens": 799})
    _row("a usage object, as JSON text", usage)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "inbox_client.py"),
              encoding="utf-8") as f:
        code = "".join(f.readlines()[:30])
    _row("30 lines of the client, as code", code)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "project_brief.txt"),
              encoding="utf-8") as f:
        brief = f.read()
    _row("the project brief, whole", brief)
    print()
    print("every count above is computed by tokenizer.py from corpus.txt --")
    print("rerun it and the numbers are identical, because the merges are.")


if __name__ == "__main__":
    main()
