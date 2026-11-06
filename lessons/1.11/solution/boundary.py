"""The boundary: every crossing gets the same question.

Lesson AIE 1.10 -- Validation at the Boundary.

Lessons 1.08 and 1.09 each guarded ONE crossing: the
model's reply on its way into the store (the record
contract), and the model's proposed calls on their way
to the world (the dispatcher). This lesson walks the
whole perimeter of the Inbox Assistant and gives every
crossing the same treatment. Three surfaces:

- REQUESTS IN -- a user request enters as an object:
  {text, requester, channel}. Contract request@1.0.0.
- RESULTS BACK -- a tool's result re-enters the
  conversation. Results travel as JSON strings and are
  checked against the returning tool's result contract
  (result@1.0.0, per tool; a get_record result embeds a
  record, which must itself satisfy record@1.0.0).
- RECORDS AT REST -- the store is read back, one JSON
  line per record, each stamped with the schema version
  that wrote it. Rest is a crossing too: what was filed
  under one version is consumed under another.

The gate, boundary@1.0.0, answers each crossing with one
of four dispositions, always with located, named
reasons:

- ADMIT -- the crossing satisfies its contract as it
  stands.
- REPAIR -- mechanical, meaning-preserving fixes make
  it satisfy the contract; every fix is logged, and the
  admitted form is the repaired one. The repair set is
  closed and printed below: strip control characters,
  normalise whitespace, drop undeclared keys from a
  closed contract, case-fold an enum value that folds
  into the set, neutralise instruction-shaped text in
  data by quoting it as data, and the VERSIONED
  MIGRATIONS -- a crossing stamped with an older
  contract version is translated by that version's
  printed migration table, never by guessing.
- QUARANTINE -- the crossing is interpretable but not
  admissible, and no mechanical rule may settle it: a
  value no version ever allowed, a text over its cap
  (truncation would rewrite it), a result under the
  wrong contract, a second record claiming an id that
  is already filed. Quarantine is a holding state with
  the reason attached; the crossing waits for a
  decision, visible, neither admitted nor dropped.
- REJECT -- the crossing cannot be interpreted under
  any contract: it does not parse, its root has the
  wrong type, a required field is absent, its channel
  is a trust zone this system does not have. Refused,
  with the reason.

Two strategies are measured against the gate in
run_boundary.py: PASS-THROUGH (no boundary: everything
is forwarded as it arrives, nothing is logged) and
REJECT-ONLY (strict validation, no repair, no
migration, no quarantine: valid as-is or refused).

The unification, measured in section 6: the 1.09
dispatcher IS this gate at one surface -- inspect_call
applies the same registry / parse / validate order to a
proposed call, and its dispositions agree with the
dispatcher's on all 35 first emissions of 1.09.

What the gate never does: it adds no model calls (the
validation is local code), it never rewrites content
(truncation, synonym mapping and silent overwriting are
decisions, not repairs), and it cannot certify truth --
a formally perfect crossing can still be wrong about
the world. That ceiling is measured, not hidden.

Standard library only.
"""

import json

import structured
import tools

# ---------------------------------------------------------------- contracts

REQUEST_SCHEMA = {
    "name": "request@1.0.0",
    "fields": {
        "text": {"type": "string", "min_length": 1, "max_length": 2000},
        "requester": {"type": "string", "min_length": 1},
        "channel": {"type": "string", "enum": ("ui", "api", "email")},
    },
    "additionalProperties": False,
}

# The result contract per tool (result@1.0.0). A get_record
# result embeds a record: the embedded value must satisfy
# record@1.0.0 (structured.validate).
RESULT_SCHEMAS = {
    "search_inbox": {"hits": "hit-list", "total": "count"},
    "get_record": {"message_id": "string", "record": "record"},
    "draft_reply": {"draft_id": "string", "message_id": "string",
                    "state": "string"},
}

# The migration tables. record@0.9.0 (the version that wrote
# the oldest lines in the store) differs from record@1.0.0
# in exactly three printed ways: due was the string "none"
# for no date; reply_needed was the string "yes"/"no"; the
# enums were written in upper case. search@0.9.0 returned
# {matches: [{id, text}], count: "<int as string>"}.
RECORD_090 = {"due_none": "none", "bool": {"yes": True, "no": False}}

DISPOSITIONS = ("admit", "repair", "quarantine", "reject")


def _type_name(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "null"


# ------------------------------------------------------------- validation

def validate_request(obj):
    """Located, named errors for request@1.0.0; empty is valid."""
    if not isinstance(obj, dict):
        return ["$: not an object (got {})".format(_type_name(obj))]
    errors = []
    fields = REQUEST_SCHEMA["fields"]
    if REQUEST_SCHEMA["additionalProperties"] is False:
        for key in obj:
            if key not in fields:
                errors.append(
                    "$.{}: unexpected key (the contract is "
                    "closed)".format(key))
    for name, spec in fields.items():
        if name not in obj:
            errors.append("$.{}: missing (required)".format(name))
            continue
        value = obj[name]
        if not isinstance(value, str):
            errors.append("$.{}: expected string, got {}".format(
                name, _type_name(value)))
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
    # canonical form for the text itself (request@1.0.0 states
    # it plainly): no control characters beyond \n and \t, LF
    # line endings, no surrounding whitespace. Dirt here is
    # mechanical -- section "repairs" in boundary.py.
    text = obj.get("text") if isinstance(obj, dict) else None
    if isinstance(text, str) and text:
        if _strip_controls(text) != text:
            errors.append("$.text: contains control or zero-width "
                          "characters")
        if "\r" in text:
            errors.append("$.text: carries CR line endings "
                          "(LF is the canonical form)")
        if text != text.strip():
            errors.append("$.text: carries leading/trailing "
                          "whitespace")
    return errors


def validate_result(tool, obj):
    """Located, named errors for result@1.0.0 (per tool)."""
    if tool not in RESULT_SCHEMAS:
        return ["$: unknown tool {!r} (no result contract)".format(tool)]
    if not isinstance(obj, dict):
        return ["$: not an object (got {})".format(_type_name(obj))]
    schema = RESULT_SCHEMAS[tool]
    errors = []
    for key in obj:
        if key not in schema:
            errors.append(
                "$.{}: unexpected key (the contract is "
                "closed)".format(key))
    for name, kind in schema.items():
        if name not in obj:
            errors.append("$.{}: missing (required)".format(name))
            continue
        value = obj[name]
        if kind == "string":
            if not isinstance(value, str):
                errors.append("$.{}: expected string, got {}".format(
                    name, _type_name(value)))
        elif kind == "count":
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append("$.{}: expected integer, got {}".format(
                    name, _type_name(value)))
            elif value < 0:
                errors.append("$.{}: {} is below zero".format(name, value))
        elif kind == "hit-list":
            if not isinstance(value, list):
                errors.append("$.{}: expected array, got {}".format(
                    name, _type_name(value)))
                continue
            for i, hit in enumerate(value):
                if not isinstance(hit, dict):
                    errors.append("$.hits[{}]: not an object".format(i))
                    continue
                for hk in hit:
                    if hk not in ("id", "snippet"):
                        errors.append(
                            "$.hits[{}].{}: unexpected key".format(i, hk))
                for hk in ("id", "snippet"):
                    if hk not in hit:
                        errors.append(
                            "$.hits[{}].{}: missing (required)".format(
                                i, hk))
                    elif not isinstance(hit[hk], str):
                        errors.append(
                            "$.hits[{}].{}: expected string".format(i, hk))
        elif kind == "record":
            for err in structured.validate(value):
                errors.append("$.record" + err[1:])
    return errors


def _parse(raw):
    """The parse step: crossings that travel as strings are
    parsed; anything already decoded passes through."""
    if isinstance(raw, str):
        try:
            return json.loads(raw), None
        except ValueError:
            return None, "$: does not parse as JSON"
    return raw, None


# ---------------------------------------------------------------- repairs

_CONTROL_OK = ("\n", "\t")
_INSTRUCTION_MARKERS = ("ignore the", "ignore previous",
                        "system note:", "system:", "disregard")


def _strip_controls(text):
    return "".join(ch for ch in text
                   if ch in _CONTROL_OK
                   or (ord(ch) >= 32 and ord(ch) != 0x7f
                       and not 0x200b <= ord(ch) <= 0x200f))


def _instruction_shaped(text):
    low = text.lower()
    return any(m in low for m in _INSTRUCTION_MARKERS)


def _repair_request(obj):
    """Mechanical fixes for a request object. Returns
    (form, log) -- the form may still fail validation."""
    form = dict(obj)
    log = []
    text = form.get("text")
    if isinstance(text, str):
        fixed = _strip_controls(text)
        if fixed != text:
            log.append("stripped control/zero-width characters "
                       "from $.text")
            text = fixed
        fixed = text.replace("\r\n", "\n").replace("\r", "\n")
        if fixed != text:
            log.append("normalised line endings in $.text")
            text = fixed
        fixed = text.strip()
        if fixed != text:
            log.append("trimmed surrounding whitespace from $.text")
            text = fixed
        form["text"] = text
    return form, log


def _drop_extra(form, allowed, where="$"):
    log = []
    for key in list(form):
        if key not in allowed:
            del form[key]
            log.append("dropped undeclared key {}.{} (closed "
                       "contract)".format(where, key))
    return log


def _case_fold_enums(record):
    """Case-fold record enum values that fold into their sets."""
    log = []
    for field in ("label", "priority"):
        value = record.get(field)
        if isinstance(value, str):
            folded = value.lower()
            enum = structured.SCHEMA["fields"][field]["enum"]
            if folded != value and folded in enum:
                record[field] = folded
                log.append("case-folded $.{} {!r} -> {!r}".format(
                    field, value, folded))
    return log


def migrate_record_090(record):
    """record@0.9.0 -> record@1.0.0, by the printed table.
    Returns (migrated, log)."""
    form = dict(record)
    log = []
    if form.get("due") == RECORD_090["due_none"]:
        form["due"] = None
        log.append("migration record@0.9.0: $.due 'none' -> null")
    if isinstance(form.get("reply_needed"), str):
        mapped = RECORD_090["bool"].get(form["reply_needed"])
        if mapped is not None:
            log.append("migration record@0.9.0: $.reply_needed "
                       "{!r} -> {}".format(form["reply_needed"], mapped))
            form["reply_needed"] = mapped
    log += _case_fold_enums(form)
    return form, log


def migrate_search_090(obj):
    """search@0.9.0 -> result@1.0.0: matches->hits,
    text->snippet, count string->int."""
    form = {"hits": [{"id": m["id"], "snippet": m["text"]}
                     for m in obj.get("matches", [])],
            "total": int(obj["count"])}
    return form, ["migration search@0.9.0: matches->hits, "
                  "text->snippet, count {!r} -> {}".format(
                      obj["count"], form["total"])]


# ------------------------------------------------------------------- gate

def _verdict(disposition, form, log, flags=()):
    return {"disposition": disposition, "form": form,
            "log": log, "flags": list(flags)}


def _inspect_request(raw):
    if not isinstance(raw, dict):
        return _verdict("reject", None,
                        ["$: not an object (got {}) -- a request "
                         "crossing must be an object".format(
                             _type_name(raw))])
    errors = validate_request(raw)
    if not errors:
        return _verdict("admit", raw, [])
    repaired, log = _repair_request(raw)
    if log and not validate_request(repaired):
        return _verdict("repair", repaired, log)
    errors = validate_request(repaired)
    text = repaired.get("text")
    channel = repaired.get("channel")
    if isinstance(text, str) and len(text) > 2000:
        return _verdict("quarantine", None,
                        ["$.text: {} chars exceeds the 2000 cap; "
                         "truncation would rewrite the request -- "
                         "held for a decision".format(len(text))])
    if isinstance(channel, str) and channel not in ("ui", "api",
                                                    "email"):
        return _verdict("reject", None,
                        ["$.channel: {!r} is not a trust zone this "
                         "system has (ui|api|email); a channel is "
                         "never guessed".format(channel)])
    return _verdict("reject", None, errors)


def _inspect_result(tool, raw):
    obj, perr = _parse(raw)
    if perr:
        return _verdict("reject", None, [perr])
    if tool not in RESULT_SCHEMAS:
        return _verdict("reject", None,
                        ["$: unknown tool {!r}".format(tool)])
    if isinstance(obj, dict) and obj.get("v") == "0.9.0" \
            and tool == "search_inbox" and "matches" in obj:
        form, log = migrate_search_090(obj)
        if not validate_result(tool, form):
            return _verdict("repair", form, log)
    errors = validate_result(tool, obj)
    if not errors:
        form, flags = obj, []
        if tool == "search_inbox":
            form, flags = _neutralise(form)
        return _verdict("repair", form, flags) if flags \
            else _verdict("admit", form, [])
    # repairable: undeclared keys only -> drop them, logged
    form = dict(obj)
    log = _drop_extra(form, RESULT_SCHEMAS[tool])
    if log and not validate_result(tool, form):
        form2, flags = _neutralise(form) if tool == "search_inbox" \
            else (form, [])
        return _verdict("repair", form2, log + flags)
    # interpretable but under the wrong contract / carrying a
    # record that fails its own contract: held, not refused
    return _verdict("quarantine", None,
                    ["result does not satisfy result@1.0.0 for "
                     "{}: {}".format(tool, "; ".join(errors))])


def _neutralise(form):
    """Instruction-shaped text inside result DATA is quoted
    as data and flagged. The content is preserved; its
    standing changes: data, never instruction."""
    form = json.loads(json.dumps(form))
    flags = []
    for hit in form.get("hits", []):
        if _instruction_shaped(hit.get("snippet", "")):
            hit["snippet"] = "[quoted data] " + hit["snippet"]
            flags.append("instruction-shaped text in a search "
                         "snippet quoted as data (it is a "
                         "result, not an instruction)")
    return form, flags


def _inspect_record(raw, seen_ids):
    obj, perr = _parse(raw)
    if perr:
        return _verdict("reject", None, [perr])
    if not isinstance(obj, dict) or "record" not in obj:
        return _verdict("reject", None,
                        ["$: not a store line (no record field)"])
    rid = obj.get("id")
    if rid in seen_ids:
        return _verdict("quarantine", None,
                        ["duplicate identity: {!r} is already "
                         "filed; a second claim is held, never "
                         "overwritten".format(rid)])
    record = obj["record"]
    if obj.get("v") == "0.9.0":
        form, log = migrate_record_090(record)
        if not structured.validate(form):
            return _verdict("repair", form, log)
        return _verdict("quarantine", None,
                        ["record@0.9.0 line does not migrate "
                         "cleanly: {}".format(
                             "; ".join(structured.validate(form)))])
    errors = structured.validate(record)
    if not errors:
        return _verdict("admit", record, [])
    form = dict(record)
    log = _case_fold_enums(form)
    if log and not structured.validate(form):
        return _verdict("repair", form, log)
    return _verdict("quarantine", None,
                    ["record fails record@1.0.0 and no mechanical "
                     "rule settles it: {}".format("; ".join(errors))])


def inspect(crossing, seen_ids=None):
    """boundary@1.0.0's answer to one crossing: a dict with
    the disposition, the admitted form (for admit/repair),
    the log of every repair applied, and any flags.
    seen_ids tracks record identities already filed in this
    read-back (duplicate detection at rest)."""
    surface = crossing["surface"]
    if surface == "request":
        return _inspect_request(crossing["wild"])
    if surface == "result":
        return _inspect_result(crossing.get("tool"),
                               crossing["wild"])
    if surface == "record":
        return _inspect_record(crossing["wild"], seen_ids or set())
    raise ValueError("unknown surface {!r}".format(surface))


# --------------------------------------------------- the 1.09 unification

def inspect_call(wire):
    """The gate at the surface 1.09 built: a proposed call.
    Same order as agent.dispatch -- registry, parse,
    validate -- without executing. Returns admit/reject."""
    name = wire["name"]
    if name not in tools.TOOL_SCHEMAS:
        return "reject"
    try:
        args = json.loads(wire["arguments"])
    except (ValueError, TypeError):
        return "reject"
    if tools.validate_args(name, args):
        return "reject"
    return "admit"


# ------------------------------------------------------- other strategies

def pass_through(crossing):
    """No boundary: the crossing is forwarded as it arrives
    (strings are decoded if they happen to parse; nothing
    is checked, nothing is logged)."""
    raw = crossing["wild"]
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return raw
    if crossing["surface"] == "record" and isinstance(raw, dict):
        return raw.get("record", raw)
    return raw


def reject_only(crossing):
    """Strict validation, no repair, no migration, no
    quarantine: returns the form if it is valid exactly as
    it stands, else None."""
    surface = crossing["surface"]
    raw = crossing["wild"]
    if surface == "request":
        return raw if isinstance(raw, dict) \
            and not validate_request(raw) else None
    if surface == "result":
        obj, perr = _parse(raw)
        if perr or not isinstance(obj, dict):
            return None
        return obj if not validate_result(
            crossing.get("tool"), obj) else None
    if surface == "record":
        obj, perr = _parse(raw)
        if perr or not isinstance(obj, dict) or "record" not in obj:
            return None
        return obj["record"] if not structured.validate(
            obj["record"]) else None
    return None


# ------------------------------------------------------------ form checks

def form_valid(crossing, form):
    """Re-validate an admitted form against its contract --
    the safety question, asked of any strategy's output."""
    if form is None:
        return False
    surface = crossing["surface"]
    if surface == "request":
        return isinstance(form, dict) and not validate_request(form)
    if surface == "result":
        return isinstance(form, dict) and not validate_result(
            crossing.get("tool"), form)
    if surface == "record":
        return isinstance(form, dict) \
            and not structured.validate(form)
    return False
