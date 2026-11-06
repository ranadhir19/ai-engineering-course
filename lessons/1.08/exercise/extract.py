"""The found extractor for Exercise 1.08 -- parse on hope.

This is the extractor as it exists wherever structured output
is consumed without a contract: take the model's reply, hand it
to json.loads, and pass whatever comes out to the code that
files records. It works beautifully on the replies that were
never broken, and on the rest it does one of two things, both
bad: it gives up (None -- the record silently never exists), or
it files whatever parsed, valid or not, into the system of
record.

Your exercise is to replace it: an extractor that files only
records satisfying record@1.0.0, repairs what is mechanically
repairable (and can show its repairs), and rejects -- by name,
inside the yield budget -- what the contract forbids it to
guess. The bars are in README.md; the harness grades this
module against them:

    python3 records_harness.py --extractor extract.py

The interface is the contract: extract(reply_text) returns a
record dict to file, or None to reject the reply.
"""

import json


def extract(reply_text):
    """Hope, as a function: parse the reply and file the result."""
    try:
        obj = json.loads(reply_text)
    except (ValueError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None
