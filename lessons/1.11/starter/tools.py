"""The tool registry: the Assistant's hands.

Lesson AIE 1.09 -- Function Calling.

Lesson 1.08 gave the model's REPLY a contract: a schema,
checked by code, with errors that are located and named.
This lesson gives the model's ACTIONS the same contract.
The Assistant stops merely describing the inbox and starts
proposing operations on it: search it, read a record back,
apply a label, draft a reply. Every proposal arrives as a
call -- a tool name plus an arguments STRING, exactly as the
provider APIs deliver it -- and every call is disposed by
code before anything in the world changes:

- REGISTRY -- the four tools that exist, each with a JSON
  Schema for its arguments (the 1.08 contract, generalised:
  the schema is now a function's signature), an access level
  (read or write), and the function that executes it. A call
  naming anything outside this registry is not an error in
  the tool; it is a proposal the code refuses.
- validate_args(name, args) -- checks parsed arguments
  against the tool's schema and returns located, named
  errors ("$.max_results: expected integer, got string"),
  in the style of 1.08's validator -- because these errors
  are also an API: the dispatcher hands them back to the
  model as a tool result, and the model corrects itself.
- execute(store, name, args) -- runs a VALIDATED call
  against the store and returns its result. Execution can
  still fail in the world (a message id that does not
  exist) -- that failure is a ToolError with a code, not a
  crash, and it travels back the same way.

The store is the Assistant's inbox: the same 24 messages
1.08 filed records for (records.json), with the labels the
Assistant applies and the drafts it creates kept as state
the harness can grade.

Standard library only.
"""

import json
import os

LABELS = ("action", "reply", "fyi", "archive")

TOOL_SCHEMAS = {
    "search_inbox": {
        "access": "read",
        "description": "Search the inbox message text; returns "
                       "the matching message ids and snippets, "
                       "in inbox order.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "max_results": {"type": "integer",
                                "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    "get_record": {
        "access": "read",
        "description": "Read back the record filed for one "
                       "message in lesson 1.08.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "minLength": 1},
            },
            "required": ["message_id"],
            "additionalProperties": False,
        },
    },
    "apply_label": {
        "access": "write",
        "description": "File one message under a label. The "
                       "label set is closed -- it is the same "
                       "enum the 1.08 record carries.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "minLength": 1},
                "label": {"type": "string", "enum": LABELS},
            },
            "required": ["message_id", "label"],
            "additionalProperties": False,
        },
    },
    "draft_reply": {
        "access": "write",
        "description": "Create a draft reply to one message. "
                       "A draft is not a send: nothing leaves "
                       "the building from this tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "minLength": 1},
                "body": {"type": "string",
                         "minLength": 1, "maxLength": 500},
            },
            "required": ["message_id", "body"],
            "additionalProperties": False,
        },
    },
}


class ToolError(Exception):
    """An execution failure in the world, with a code the
    dispatcher can hand back to the model."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# ------------------------------------------------------------------ store

class Store:
    """The inbox and the state the tools create. Built from
    records.json (the 1.08 case set): each message carries
    the record 1.08 filed for it. Labels applied and drafts
    created during a run are this run's state."""

    def __init__(self, cases):
        self.messages = {
            c["id"]: {"email": c["email"], "record": c["gold"]}
            for c in cases
        }
        self.labels = {}
        self.drafts = []

    @classmethod
    def from_records(cls, path=None):
        if path is None:
            path = os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "records.json")
        with open(path) as f:
            return cls(json.load(f)["cases"])


# -------------------------------------------------------------- validation

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


def validate_args(name, args):
    """Check parsed arguments against the named tool's JSON
    Schema. Returns located, named errors; empty is valid.
    (The subset of JSON Schema these signatures use: type,
    enum, required, additionalProperties, minimum/maximum,
    minLength/maxLength.)"""
    if name not in TOOL_SCHEMAS:
        return ["$: unknown tool {!r} (not in the registry)".format(name)]
    schema = TOOL_SCHEMAS[name]["parameters"]
    if not isinstance(args, dict):
        return ["$: arguments must be an object, got "
                + _type_name(args)]
    errors = []
    props = schema["properties"]
    if schema.get("additionalProperties") is False:
        for key in args:
            if key not in props:
                errors.append(
                    "$.{}: unexpected argument (the signature "
                    "is closed)".format(key))
    for field in schema.get("required", []):
        if field not in args:
            errors.append("$.{}: missing (required)".format(field))
    for field, spec in props.items():
        if field not in args:
            continue
        value = args[field]
        kind = spec["type"]
        if kind == "string":
            if not isinstance(value, str):
                errors.append("$.{}: expected string, got {}".format(
                    field, _type_name(value)))
                continue
            if "enum" in spec and value not in spec["enum"]:
                errors.append("$.{}: {!r} is not one of {}".format(
                    field, value, "|".join(spec["enum"])))
            if "minLength" in spec and len(value) < spec["minLength"]:
                errors.append("$.{}: {} chars is below the "
                              "minimum {}".format(
                                  field, len(value), spec["minLength"]))
            if "maxLength" in spec and len(value) > spec["maxLength"]:
                errors.append("$.{}: {} chars exceeds the "
                              "maximum {}".format(
                                  field, len(value), spec["maxLength"]))
        elif kind == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append("$.{}: expected integer, got {}".format(
                    field, _type_name(value)))
                continue
            if "minimum" in spec and value < spec["minimum"]:
                errors.append("$.{}: {} is below the minimum "
                              "{}".format(field, value, spec["minimum"]))
            if "maximum" in spec and value > spec["maximum"]:
                errors.append("$.{}: {} exceeds the maximum "
                              "{}".format(field, value, spec["maximum"]))
    return errors


# -------------------------------------------------------------- execution

def _search(store, args):
    query = args["query"].lower()
    limit = args.get("max_results", 5)
    hits = []
    for mid, msg in store.messages.items():
        if query in msg["email"].lower():
            hits.append({"id": mid, "snippet": msg["email"][:72]})
    return {"hits": hits[:limit], "total": len(hits)}


def _get_record(store, args):
    mid = args["message_id"]
    if mid not in store.messages:
        raise ToolError("NOT_FOUND",
                        "no message with id {!r}".format(mid))
    return {"message_id": mid,
            "record": store.messages[mid]["record"]}


def _apply_label(store, args):
    mid = args["message_id"]
    if mid not in store.messages:
        raise ToolError("NOT_FOUND",
                        "no message with id {!r}".format(mid))
    store.labels[mid] = args["label"]
    return {"message_id": mid, "label": args["label"],
            "state": "labelled"}


def _draft_reply(store, args):
    mid = args["message_id"]
    if mid not in store.messages:
        raise ToolError("NOT_FOUND",
                        "no message with id {!r}".format(mid))
    draft = {"draft_id": "draft-{:02d}".format(len(store.drafts) + 1),
             "message_id": mid, "body": args["body"]}
    store.drafts.append(draft)
    return {"draft_id": draft["draft_id"], "message_id": mid,
            "state": "draft created (not sent)"}


_EXECUTORS = {
    "search_inbox": _search,
    "get_record": _get_record,
    "apply_label": _apply_label,
    "draft_reply": _draft_reply,
}


def execute(store, name, args):
    """Run a call's function against the store. Callers are
    expected to have validated first (agent.dispatch does);
    the naive executor in agent.py calls this directly, on
    purpose, to show what validation is for."""
    return _EXECUTORS[name](store, args)


def render_registry():
    """The registry as it is handed to the model: names,
    descriptions, and the JSON Schema of each signature."""
    return {
        name: {"description": spec["description"],
               "access": spec["access"],
               "parameters": spec["parameters"]}
        for name, spec in TOOL_SCHEMAS.items()
    }
