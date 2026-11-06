"""The budgeter: a token counter and a context budget inside the client.

Lesson AIE 1.03 -- Tokens & Context Windows.

Two pieces:

``BudgetedProviderClient`` -- a ProviderClient that counts before it
sends. If the prompt's token count plus the caller's stated reserve
(for the answer) exceeds the provider's window, it raises
``BudgetExceededError`` *before any request is made*: the wall is met
in your own code, with your own numbers, instead of as a 400 from the
server after the round trip.

``fit_documents`` -- the fitting policy. Given a token budget for the
prompt, it walks the documents in relevance order (see
documents.py) and includes each whole while it fits. A document that
does not fit whole is included as its longest whole-sentence prefix
that fits, provided at least ``MIN_USEFUL_TOKENS`` of room remain;
otherwise it is skipped. The system message and the question are
never touched. Every document that is not included whole is
accounted for in the returned loss log -- a loss that is not logged
did not, for engineering purposes, get decided; it just happened.
"""

import re

from inbox_client import PROVIDERS, ProviderClient
from tokenizer import count_messages_tokens, count_tokens

MIN_USEFUL_TOKENS = 120

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class BudgetExceededError(Exception):
    """The prompt, counted locally, does not fit the window.

    Raised before any request is sent; the message carries the
    numbers (counted prompt tokens, reserve, window) so the caller
    decides with measurements, as everywhere in this course.
    """

    def __init__(self, provider, prompt_tokens, reserve_tokens, window):
        self.provider = provider
        self.prompt_tokens = prompt_tokens
        self.reserve_tokens = reserve_tokens
        self.window = window
        super().__init__(
            "budget exceeded for "
            + provider
            + ": prompt_tokens "
            + str(prompt_tokens)
            + " + reserve "
            + str(reserve_tokens)
            + " exceeds context window "
            + str(window)
        )


class BudgetedProviderClient(ProviderClient):
    """ProviderClient with a pre-flight budget check.

    ``reserve_tokens`` is the caller's stated allowance for the
    answer -- the window must hold the reply as well as the prompt,
    and a budget that forgets the reply is how windows get hit from
    the far side.
    """

    def __init__(self, provider_name, reserve_tokens=0, **kwargs):
        super().__init__(provider_name, **kwargs)
        self.reserve_tokens = reserve_tokens
        self.window = PROVIDERS[provider_name]["context_tokens"]

    def chat(self, messages, temperature=0.2):
        prompt_tokens = count_messages_tokens(messages)
        if prompt_tokens + self.reserve_tokens > self.window:
            raise BudgetExceededError(
                self.provider_name, prompt_tokens, self.reserve_tokens, self.window
            )
        return super().chat(messages, temperature=temperature)


def _sentences(text):
    return [s for s in _SENTENCE_END.split(text.strip()) if s]


def fit_documents(documents, budget_tokens):
    """Fit documents into ``budget_tokens`` of prompt space.

    ``documents`` is the ranked list from documents.rank_documents.
    The space is shared with the fixed parts (system + question),
    which are counted first and never shed. Returns
    ``(messages, losses)``: the messages to send, and one loss entry
    per document not included whole --
    {"document", "action": "truncated"|"skipped",
     "kept_tokens", "dropped_tokens"}.
    """
    from documents import doc_block, fixed_messages

    # Accounting is exact, not estimated: every candidate prompt is
    # assembled and counted whole, because a budget checked with an
    # estimate is a budget that leaks by the size of the estimate.
    blocks = []
    losses = []
    for doc in documents:
        block = doc_block(doc["name"], doc["text"])
        block_tokens = count_tokens(block)
        if count_messages_tokens(fixed_messages(blocks + [block])) <= budget_tokens:
            blocks.append(block)
            continue
        # Does not fit whole. Keep the longest whole-sentence prefix
        # that fits, if the remaining room is worth using at all.
        remaining = budget_tokens - count_messages_tokens(fixed_messages(blocks))
        kept_text = ""
        if remaining >= MIN_USEFUL_TOKENS:
            acc = []
            for sentence in _sentences(doc["text"]):
                trial = doc_block(doc["name"], " ".join(acc + [sentence]))
                if count_messages_tokens(fixed_messages(blocks + [trial])) > budget_tokens:
                    break
                acc.append(sentence)
            if acc:
                kept_text = " ".join(acc)
        if kept_text:
            kept_block = doc_block(doc["name"], kept_text)
            blocks.append(kept_block)
            kept_tokens = count_tokens(kept_block)
            losses.append(
                {
                    "document": doc["name"],
                    "action": "truncated",
                    "kept_tokens": kept_tokens,
                    "dropped_tokens": block_tokens - kept_tokens,
                }
            )
        else:
            losses.append(
                {
                    "document": doc["name"],
                    "action": "skipped",
                    "kept_tokens": 0,
                    "dropped_tokens": block_tokens,
                }
            )
    return fixed_messages(blocks), losses
