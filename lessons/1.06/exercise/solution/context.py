"""Exercise 1.06 -- the worked solution.

``assemble`` delegates to the lesson's context assembler
(../solution/context.py): the instructions and the question
pinned, examples capped, documents ranked with the strongest
speaking last, history compacted rather than silently dropped,
and every item accounted for in the report. It passes all four
checks on all ten scenarios; run_context.py in ../solution/
reproduces the naive-vs-policy comparison it comes from.
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "..", "solution"))

import context as _library  # noqa: E402


def assemble(scenario):
    return _library.assemble(
        scenario["question"],
        budget_tokens=scenario["budget_tokens"],
        examples=scenario["examples"],
        documents=scenario["documents"],
        history=scenario["history"])
