"""The worked solution for Exercise 1.07: the lesson's settings.

The exercise surface is a settings dict, so the worked solution
is one: it delegates to sampling@1.0.0, the policy Lesson 1.07
measured and shipped in ../../solution/sampling.py -- greedy
where one right answer exists, the model's own distribution
with its tail cut where variety is the product. The harness
grades this module's SETTINGS exactly as it grades yours.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "..", "..", "solution"))

from sampling import SETTINGS  # noqa: E402,F401  (the deliverable)
