"""A token counter you can read: byte-pair encoding, built in the open.

Lesson AIE 1.03 -- Tokens & Context Windows.
Standard library only.

Until now the course counted "tokens" the way the stand-in servers
meter: whitespace words. Real providers meter in *tokens* -- subword
units produced by a tokenizer. This module builds one, the way the
real ones are built:

1. Pre-tokenise: split text into word pieces, number pieces,
   punctuation pieces and whitespace runs (a regex, below). Merges
   never cross a piece boundary.
2. Start from bytes: every piece begins as its UTF-8 bytes, so the
   initial vocabulary is the 256 byte values and nothing is ever
   out-of-vocabulary.
3. Train: count adjacent symbol pairs across the corpus; merge the
   most frequent pair into a new symbol; repeat. Ties break toward
   the lexicographically smallest pair, so training is deterministic:
   same corpus, same merges, on any machine.
4. Encode: apply the merges to a new text in the order they were
   learned. The token count of a text is the length of its encoding.

Two properties the lesson relies on, both provable from the rules
above: every whitespace word yields at least one token, so a token
count is never smaller than the word count; and the counter is
deterministic, so a budget checked with it is a budget kept.

The trained merges are cached beside this file as
``tokenizer_merges.json`` on first use (training on the bundled
corpus takes about a minute in pure Python); delete the cache to
retrain from scratch.
"""

import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_PATH = os.path.join(HERE, "corpus.txt")
MERGES_PATH = os.path.join(HERE, "tokenizer_merges.json")
NUM_MERGES = 1500

_PIECES = re.compile(r"[A-Za-z]+|[0-9]+|[^\sA-Za-z0-9]|\s+")


def _pieces(text):
    return _PIECES.findall(text)


def _train(corpus_text, num_merges=NUM_MERGES):
    """Learn merges from text. A symbol is a bytes object (one byte
    at first, longer after merges); returns a list of
    (symbol_a, symbol_b) pairs in learned order."""
    sequences = [
        [bytes([b]) for b in piece.encode("utf-8")] for piece in _pieces(corpus_text)
    ]
    merges = []
    for _ in range(num_merges):
        counts = Counter()
        for seq in sequences:
            for i in range(len(seq) - 1):
                counts[(seq[i], seq[i + 1])] += 1
        if not counts:
            break
        best = min(counts, key=lambda p: (-counts[p], p))
        if counts[best] < 2:
            break
        merges.append(best)
        merged = best[0] + best[1]
        new_sequences = []
        for seq in sequences:
            out = []
            i = 0
            while i < len(seq):
                if i < len(seq) - 1 and seq[i] == best[0] and seq[i + 1] == best[1]:
                    out.append(merged)
                    i += 2
                else:
                    out.append(seq[i])
                    i += 1
            new_sequences.append(out)
        sequences = new_sequences
    return merges


class Tokenizer:
    """A byte-pair tokenizer built from an ordered merges list.

    ``merges`` is a list of (bytes, bytes) pairs; rank in the list is
    the order the merges were learned, and encoding always applies
    the lowest-ranked (earliest-learned) merge available first --
    the standard BPE encoding rule.
    """

    def __init__(self, merges):
        self.merges = list(merges)
        self.ranks = {pair: i for i, pair in enumerate(self.merges)}

    @property
    def vocab_size(self):
        return 256 + len(self.merges)

    def encode(self, text):
        """Encode text to a list of tokens (bytes objects)."""
        tokens = []
        for piece in _pieces(text):
            seq = tuple(bytes([b]) for b in piece.encode("utf-8"))
            while len(seq) > 1:
                best_i = None
                best_rank = None
                for i in range(len(seq) - 1):
                    rank = self.ranks.get((seq[i], seq[i + 1]))
                    if rank is not None and (best_rank is None or rank < best_rank):
                        best_rank = rank
                        best_i = i
                if best_i is None:
                    break
                seq = seq[:best_i] + (seq[best_i] + seq[best_i + 1],) + seq[best_i + 2:]
            tokens.extend(seq)
        return tokens

    def count(self, text):
        return len(self.encode(text))


_CACHE = None


def get_tokenizer():
    """The pack tokenizer: load the cached merges, or train on the
    bundled corpus and cache them."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if os.path.exists(MERGES_PATH):
        with open(MERGES_PATH, encoding="utf-8") as f:
            stored = json.load(f)["merges"]
        merges = [(bytes.fromhex(a), bytes.fromhex(b)) for a, b in stored]
    else:
        with open(CORPUS_PATH, encoding="utf-8") as f:
            corpus = f.read()
        learned = _train(corpus)
        merges = list(learned)
        with open(MERGES_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"num_merges": len(merges),
                 "merges": [[a.hex(), b.hex()] for a, b in merges]},
                f,
            )
    _CACHE = Tokenizer(merges)
    return _CACHE


def count_tokens(text):
    """The lesson's meter: BPE tokens in ``text``."""
    return get_tokenizer().count(text)


def count_messages_tokens(messages):
    """Tokens in a chat prompt: every message content, counted the
    way a provider meters the prompt it receives."""
    return sum(count_tokens(str(m.get("content", ""))) for m in messages)


def word_count(text):
    """The 1.01/1.02 meter, kept for comparison: whitespace words."""
    return len(text.split())
