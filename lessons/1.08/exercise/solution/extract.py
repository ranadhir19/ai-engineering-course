"""The worked solution for Exercise 1.08.

Delegates to the lesson's shipped machinery: the deterministic
repair layer plus the validator from ../solution/structured.py.
A reply is filed only when the repaired value validates against
record@1.0.0; everything else is rejected -- here, by returning
None, which the harness counts against yield, exactly as the
bars intend. There is no model to re-ask in this exercise (the
replies are data), so the loop is not available: rejection is
the honest end of the road for a missing key, an enum synonym,
and a reply that stops mid-string.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "solution"))

import structured  # noqa: E402


def extract(reply_text):
    record, _repairs, _errors = structured.repair(reply_text)
    return record
