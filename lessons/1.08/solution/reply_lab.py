"""The stand-in model for Lesson 1.08 -- a wild-reply lab.

The earlier stand-ins each modelled one step of the call. This one
models the step 1.08 is about: what a production model's reply
actually looks like when the caller asks for structured output.
Given a case from records.json, the lab produces the raw reply
string a real model produces -- its CONTENT is a record it fully
intends (the case's intended record), but its FORM is the wild:
fences, prose around the payload, trailing commas, Python reprs,
string booleans, drifted enums, missing keys, invented keys,
local date formats, over-long strings, and once, a reply that
simply stops.

The lab's rules are its contract, printed here:

1. CONTENT. The model's judgement is the case's intended record:
   the gold record, except for three named cases whose intended
   record carries a judgement error (rec-07 files a task as a
   question, rec-13 escalates a notice to high priority, rec-16
   adds a week to a due date). No mode of this lab, and no
   strategy in structured.py, ever changes the intended record.
   Form machinery moves form. It does not manufacture judgement.

2. FORM (mode "ask"). The intended record is serialised with the
   case's printed defects applied: fence (markdown code fence),
   prose (a sentence before and after), trailing (trailing
   commas), pyrepr (a Python dict repr: single quotes, True,
   False, None), bool_str (reply_needed as "yes"/"no"),
   missing_due (the due key omitted), extra_field (an invented
   "confidence" key), enum_case (Action, HIGH), enum_synonym
   (priority in a neighbouring vocabulary: medium for normal),
   date_fmt (due as "18 Nov 2026" or "November 11, 2026"),
   long_summary (the intended summary itself exceeds the
   schema's 120-character cap), truncated (the reply stops
   mid-string). Defects compose, as they do in the wild.

3. RE-ASK (mode "reask"). Handed the validator's located error
   list, the lab models a cooperative model: every form defect
   the errors name is dropped on the next reply, and an
   over-long summary is shortened to the cap at a word boundary
   (the model rewrites; it does not argue). Content is
   untouched -- rule 1. A stubborn model exists in the world;
   this lab is not it, and the lesson says so: the loop's
   premise is a model that reads its error messages.

4. CONSTRAINED (mode "constrained"). A schema-guided emitter:
   the record is written key by key in schema order with types
   enforced as each value is produced, so no form defect can
   occur -- validity by construction. The one place the
   constraint bites content-shaped text is the summary cap: an
   over-long summary is cut at a word boundary to fit, the way
   a length-capped grammar forces a stop. What the emitter
   cannot do is reconsider a value: rec-07 is filed wrong,
   validly, every time.

The ask itself (ASK_TEMPLATE) names every field and says
"nothing else" -- the strongest form of the request this course
knows how to write (1.05's discipline). The lesson's claim is
that even this ask returns the wild, because a request is not
a contract. The replies are deterministic: same case in, same
string out, in every mode.

Standard library only.
"""

import json

ASK_TEMPLATE = (
    "File this email as a triage record. Reply with a JSON object "
    "with keys label, priority, summary, reply_needed, due -- "
    "and nothing else.\n\nEmail: {email}"
)

_SUMMARY_CAP = 120
_DATE_FORMATS = ("%d %b %Y", "%B %d, %Y")
_SYNONYMS = {"high": "urgent", "normal": "medium", "low": "minor"}


def _shorten(summary, cap=_SUMMARY_CAP):
    """Cut at the last word boundary at or under the cap."""
    if len(summary) <= cap:
        return summary
    cut = summary[:cap].rsplit(" ", 1)[0]
    return cut.rstrip(",;")


def _mangle(case):
    """The intended record with the value-level defects applied."""
    rec = dict(case["intended"])
    defects = case["defects"]
    if "missing_due" in defects:
        rec.pop("due", None)
    if "extra_field" in defects:
        rec["confidence"] = 0.92
    if "bool_str" in defects:
        rec["reply_needed"] = "yes" if rec["reply_needed"] else "no"
    if "enum_case" in defects:
        rec["label"] = rec["label"].capitalize()
        rec["priority"] = rec["priority"].upper()
    if "enum_synonym" in defects:
        rec["priority"] = _SYNONYMS[rec["priority"]]
    if "date_fmt" in defects and rec.get("due"):
        from datetime import date
        y, m, d = (int(x) for x in rec["due"].split("-"))
        fmt = _DATE_FORMATS[sum(ord(c) for c in case["id"]) % 2]
        rec["due"] = date(y, m, d).strftime(fmt)
    return rec


def _dump(rec, defects):
    if "pyrepr" in defects:
        text = repr(rec)
    else:
        text = json.dumps(rec, indent=1, ensure_ascii=False)
        if "trailing" in defects:
            text = text.rstrip()
            assert text.endswith("}")
            text = text[:-1].rstrip() + ",\n}"
    if "fence" in defects:
        text = "```json\n" + text + "\n```"
    if "prose" in defects:
        text = ("Here is the record for this email:\n" + text
                + "\nLet me know if you need anything else.")
    if "truncated" in defects:
        text = text[: int(len(text) * 0.6)]
    return text


def respond(case):
    """Mode 'ask': the raw reply to the filed ask."""
    return _dump(_mangle(case), case["defects"])


def reask(case, errors):
    """Mode 'reask': the reply after the validator's errors are
    handed back. Form defects are dropped; an over-long summary
    is shortened to the cap; content (rule 1) never changes."""
    rec = dict(case["intended"])
    rec["summary"] = _shorten(rec["summary"])
    return json.dumps(rec, indent=1, ensure_ascii=False)


def constrained(case):
    """Mode 'constrained': schema-guided emission. Types and the
    summary cap are enforced as values are produced; the values
    themselves are the intended ones, judgement included."""
    src = case["intended"]
    rec = {
        "label": src["label"],
        "priority": src["priority"],
        "summary": _shorten(src["summary"]),
        "reply_needed": bool(src["reply_needed"]),
        "due": src["due"],
    }
    return json.dumps(rec, indent=1, ensure_ascii=False)


def render_ask(case):
    """The full ask text for a case (used for pricing)."""
    return ASK_TEMPLATE.format(email=case["email"])
