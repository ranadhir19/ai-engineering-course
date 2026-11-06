"""Exercise 1.05 -- the worked solution.

``build_messages`` delegates to the lesson's prompt-template
library (../solution/prompts.py) at its current version: the
failing prompt, engineered -- instructions, structure, examples --
and pinned by the same 20 cases that grade it here. It scores
20/20; the version history that got it there is the library's
changelog, and run_prompts.py in ../solution/ reproduces every
step's score.
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "..", "solution"))

import prompts as _library  # noqa: E402


def build_messages(email_text):
    return _library.render("triage", email=email_text)
