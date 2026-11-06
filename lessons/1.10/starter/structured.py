"""Structured outputs: the reply gets a contract.

Lesson AIE 1.08 -- Structured Outputs.

The Inbox Assistant's triage (1.05) files a label, and downstream
code consumes it strictly. The digest and the router now need
more than a label: a record -- label, priority, a one-line
summary, whether a reply is needed, a due date. This module is
the machinery that makes a model's reply into such a record, or
refuses to:

- SCHEMA -- the contract, as data: five fields, their types, the
  two closed enums, the summary cap, due as an ISO date or null,
  every field required (null is a value; absence is a breach),
  and no additional keys. The schema is record@1.0.0.
- validate(record) -- checks a parsed record against the schema
  and returns located, named errors ("$.priority: 'urgent' is
  not one of high|normal|low"). The error list is an API: the
  repair loop hands it back to the model verbatim.
- repair(text) -- the deterministic repair layer. Every repair
  is mechanical (a fence is stripped, a span extracted, a
  trailing comma dropped, a repr parsed, an extra key dropped,
  an enum case-folded, a string boolean coerced, a named date
  format normalised) and every repair is LOGGED -- the layer
  has no silent moves. What no mechanical rule covers -- a
  missing required key, a synonym outside the enum, a summary
  over the cap, a reply that stops mid-string -- is not
  repaired. It is rejected, or escalated to the loop.
- file_record(case) -- the shipped pipeline, structured@1.0.0:
  ask once; validate strictly; repair; validate again; hand
  the errors back for ONE re-ask; validate; file the record or
  reject the case under its own name. Nothing unvalidated is
  ever filed, and nothing rejected is silent.

Measured against the ask alone (run_records.py reproduces every
number): the ask is a request, and requests are honoured at the
model's convenience. The contract is what the code enforces.

Standard library only.
"""

import ast
import json
import re
from datetime import datetime

import reply_lab
from count_tokens import count_tokens
from inbox_client import PROVIDERS

SCHEMA = {
    "name": "record@1.0.0",
    "fields": {
        "label": {"type": "string",
                  "enum": ("action", "reply", "fyi", "archive")},
        "priority": {"type": "string",
                     "enum": ("high", "normal", "low")},
        "summary": {"type": "string", "min_length": 1, "max_length": 120},
        "reply_needed": {"type": "boolean"},
        "due": {"type": "date-or-null"},
    },
    "additionalProperties": False,
}

FIELDS = tuple(SCHEMA["fields"])
_DATE_FORMATS = ("%d %b %Y", "%B %d, %Y", "%Y/%m/%d", "%d/%m/%Y")
_BOOL_STRINGS = {"yes": True, "no": False, "true": True, "false": False}

REASK_TEMPLATE = (
    "That reply was not a valid record. Errors:\n{errors}\n"
    "Reply with the corrected JSON object only."
)


# ---------------------------------------------------------------- schema

def _is_iso_date(value):
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate(record):
    """Return the list of located errors; empty means the record
    satisfies record@1.0.0 and may be filed."""
    if not isinstance(record, dict):
        return ["$: not an object"]
    errors = []
    for key in record:
        if key not in SCHEMA["fields"]:
            errors.append(
                "$.{}: unexpected key (the schema is closed)".format(key))
    for name, spec in SCHEMA["fields"].items():
        if name not in record:
            errors.append(
                "$.{}: missing (required; null is a value, "
                "absence is not)".format(name))
            continue
        value = record[name]
        kind = spec["type"]
        if kind == "string":
            if not isinstance(value, str):
                errors.append("$.{}: expected string, got {}".format(
                    name, type(value).__name__))
                continue
            if "enum" in spec and value not in spec["enum"]:
                errors.append("$.{}: {!r} is not one of {}".format(
                    name, value, "|".join(spec["enum"])))
            if "min_length" in spec and len(value) < spec["min_length"]:
                errors.append("$.{}: empty (minimum {} character)".format(
                    name, spec["min_length"]))
            if "max_length" in spec and len(value) > spec["max_length"]:
                errors.append("$.{}: {} chars exceeds the {} cap".format(
                    name, len(value), spec["max_length"]))
        elif kind == "boolean":
            if not isinstance(value, bool):
                errors.append("$.{}: expected boolean, got {}".format(
                    name, type(value).__name__))
        elif kind == "date-or-null":
            if value is not None and not _is_iso_date(value):
                errors.append(
                    "$.{}: {!r} is not an ISO date (YYYY-MM-DD) "
                    "or null".format(name, value))
    return errors


# ---------------------------------------------------------------- repair

def _parse(text, repairs):
    """Parse the reply text to an object, logging the mechanical
    rescues used. Returns the object or None."""
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    if fixed != text:
        try:
            obj = json.loads(fixed)
            repairs.append("drop-trailing-commas")
            return obj
        except ValueError:
            pass
    try:
        obj = ast.literal_eval(text)
        if isinstance(obj, dict):
            repairs.append("parse-python-repr")
            return obj
    except (ValueError, SyntaxError):
        pass
    return None


def repair(text):
    """The deterministic repair layer. Returns (record, repairs,
    errors): record is set only when the repaired value validates;
    errors is the validator's verdict on the best parse."""
    repairs = []
    work = text.strip()
    if "```" in work:
        inner = work.split("```", 2)
        if len(inner) >= 2:
            body = inner[1]
            if body.startswith("json"):
                body = body[4:]
            work = body.strip()
            repairs.append("strip-fence")
    if not work.startswith("{"):
        start, end = work.find("{"), work.rfind("}")
        if start != -1 and end > start:
            work = work[start:end + 1]
            repairs.append("extract-json-span")
    obj = _parse(work, repairs)
    if obj is None:
        return None, repairs, ["$: unparseable as JSON or a Python repr"]
    if not isinstance(obj, dict):
        return None, repairs, ["$: not an object"]
    rec = dict(obj)
    for key in list(rec):
        if key not in SCHEMA["fields"]:
            del rec[key]
            repairs.append("drop-key:" + key)
    for name in ("label", "priority"):
        value = rec.get(name)
        enum = SCHEMA["fields"][name].get("enum", ())
        if isinstance(value, str) and value not in enum \
                and value.lower() in enum:
            rec[name] = value.lower()
            repairs.append("enum-case:" + name)
    value = rec.get("reply_needed")
    if isinstance(value, str) and value.lower() in _BOOL_STRINGS:
        rec["reply_needed"] = _BOOL_STRINGS[value.lower()]
        repairs.append("bool-string:reply_needed")
    elif isinstance(value, int) and not isinstance(value, bool) \
            and value in (0, 1):
        rec["reply_needed"] = bool(value)
        repairs.append("bool-int:reply_needed")
    value = rec.get("due")
    if isinstance(value, str) and not _is_iso_date(value):
        for fmt in _DATE_FORMATS:
            try:
                rec["due"] = datetime.strptime(value, fmt).strftime("%Y-%m-%d")
                repairs.append("date-format:due")
                break
            except ValueError:
                continue
    errors = validate(rec)
    return (rec if not errors else None), repairs, errors


# ---------------------------------------------------------------- strategies

def strict_filing(text):
    """The ask-only pipeline: json.loads of the whole reply, then
    validate. Returns (record, stage, errors) with stage one of
    'parse', 'validate', 'filed'."""
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return None, "parse", ["$: unparseable as JSON"]
    errors = validate(obj)
    if errors:
        return None, "validate", errors
    return obj, "filed", []


def file_record(case, max_reasks=1):
    """structured@1.0.0: ask, validate, repair, re-ask once on
    the validator's errors, then file or reject -- named either
    way. Returns (record_or_None, log) where the log lists calls,
    repairs and the final state."""
    log = {"case": case["id"], "calls": 0, "repairs": [], "state": None}
    text = reply_lab.respond(case)
    log["calls"] += 1
    rec, stage, errors = strict_filing(text)
    if rec is not None:
        log["state"] = "filed-clean"
        return rec, log
    rec, repairs, errors = repair(text)
    log["repairs"] = repairs
    if rec is not None:
        log["state"] = "filed-repaired"
        return rec, log
    for _ in range(max_reasks):
        text = reply_lab.reask(case, errors)
        log["calls"] += 1
        rec, stage, errors = strict_filing(text)
        if rec is not None:
            log["state"] = "filed-reasked"
            return rec, log
    log["state"] = "rejected"
    log["errors"] = errors
    return None, log


# ---------------------------------------------------------------- metrics

def field_accuracy(filed, cases):
    """Per-field accuracy over the filed records: every field
    exact, except the summary, which is graded on carrying the
    case's printed key phrase (a summary's job is the fact, not
    the wording). Returns (accuracy, wrong) with wrong a list of
    (case, field)."""
    by_id = {c["id"]: c for c in cases}
    right = total = 0
    wrong = []
    for cid, rec in filed.items():
        gold = by_id[cid]["gold"]
        for field in FIELDS:
            total += 1
            if field == "summary":
                ok = by_id[cid]["summary_key"].lower() in rec[field].lower()
            else:
                ok = rec[field] == gold[field]
            right += ok
            if not ok:
                wrong.append((cid, field))
    return (right / total if total else 0.0), wrong


def record_exact(filed, cases):
    by_id = {c["id"]: c for c in cases}
    exact = sum(1 for cid, rec in filed.items() if rec == by_id[cid]["gold"])
    return exact


def price_call(prompt_text, reply_text):
    """One call on atlas, counted with the pack's BPE counter."""
    rates = PROVIDERS["atlas"]
    return (count_tokens(prompt_text) * rates["price_in_per_mtok"] / 1e6
            + count_tokens(reply_text) * rates["price_out_per_mtok"] / 1e6)
