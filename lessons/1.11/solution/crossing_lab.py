"""The crossing specimens for Lesson 1.10.

Earlier stand-ins modelled what a model says (1.05,
1.08) and what it proposes (1.09). This one models what
ARRIVES at a system boundary: the traffic itself. The
specimens live in crossings.json, each authored as an
intended form (what the crossing should be under its
contract) and the wild form that actually arrives, with
the defect tags that separate them printed in the data.
The wild forms were produced from the intended ones by
these printed rules:

- REQUESTS travel as decoded objects from the transport.
  Their defects: empty_text (the text is empty),
  control_chars (NUL, bell and zero-width characters
  ride inside a legitimate text), over_cap (the text
  runs past the contract's 2000-char cap),
  unknown_channel (a channel that is not a trust zone
  this system has), wrong_root_type (the crossing is a
  list, not an object), missing_field (a required field
  is absent), whitespace (CRLF endings and padding).
- RESULTS travel as JSON strings, as 1.09's calls did.
  Their defects: old_version_shape (a result stamped
  search@0.9.0: matches/text fields and the count as a
  string), extra_field (an undeclared key rides along),
  instruction_shaped (a snippet carries text shaped
  like an instruction to the model), drifted_record (a
  get_record result whose embedded record fails
  record@1.0.0), unparseable (the string stops
  mid-object), wrong_contract (a well-formed result
  under another tool's contract).
- RECORDS AT REST are lines of store_snapshot.jsonl:
  {id, v, record}. Their defects: version_drift (the
  line is stamped record@0.9.0 and written in that
  version's forms), unparseable (the line stops
  mid-record: bit rot), value_never_allowed (a value
  no schema version has ever allowed), over_cap (a
  summary written past the cap by an old writer),
  duplicate_id (a second line claims an id already
  filed, with different content), valid_but_wrong (the
  line satisfies every field of the contract and its
  content is the 1.09 judgement error, filed
  faithfully).

Two crossings carry valid_but_wrong (rq-10, rr-13):
formally perfect, wrong about the world. No strategy in
run_boundary.py -- pass-through, reject-only, or the
gate -- can see them. That is not a defect of the
specimens; it is the lesson's ceiling, planted in the
open, exactly as 1.08 and 1.09 planted theirs.

Golds were written in crossings.json before any gate
ran: the disposition each crossing should receive
(admit / repair / quarantine / reject) and, for
admissible crossings, the intended form the gate's
output is checked against.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = json.load(open(os.path.join(HERE, "crossings.json")))
CROSSINGS = DOC["crossings"]


def specimens():
    return CROSSINGS


def by_surface(surface):
    return [c for c in CROSSINGS if c["surface"] == surface]


def defect_census():
    from collections import Counter
    census = Counter()
    for c in CROSSINGS:
        for d in c["defects"]:
            census[d] += 1
    return census
