"""The stand-in model for Lesson 1.09 -- a tool-calling lab.

Earlier stand-ins modelled what a model SAYS. This one
models what a model PROPOSES: given a task from
tool_tasks.json, the lab emits tool calls in the wire shape
the provider APIs use -- a tool name, and the arguments as
a JSON STRING (the model emits text; the string is the
border between the model and your code). Its rules are its
contract, printed here:

1. INTENT. Each task's plan is fixed: a list of turns, each
   turn a list of intended calls (name + arguments). Two
   calls in one turn are the parallel case: independent
   proposals the model makes in a single breath. Three
   tasks carry named JUDGEMENT errors in their intended
   calls (a label chosen for the wrong reason, a search
   whose first hit is the wrong message, a draft addressed
   to the wrong one of two same-sender messages). No
   dispatcher in agent.py ever changes an intended call's
   content. Disposal machinery moves form and authority.
   It does not manufacture judgement.

2. EMISSION (the wild, for calls). The intended call is
   serialised with the call's printed defects applied:
   args_trailing (a trailing comma in the arguments
   string), args_single_quotes (a Python-repr string:
   single quotes, True, None), type_string_int (an integer
   argument emitted as a string, "5"), missing_arg (a
   required argument dropped), extra_arg (an argument the
   signature never declared), enum_drift (a label in a
   neighbouring vocabulary: "act" for action), body_over
   (a draft body past the signature's length cap),
   unknown_tool (a call to send_reply -- a tool the
   registry does not contain), bad_id (a message id that
   does not exist: formally valid, wrong in the world).

3. CORRECTION. Handed a located error (the dispatcher's
   error result), the lab models a cooperative model: it
   re-emits the call it intended with the named defect
   removed -- the arguments string is clean JSON, types
   are the schema's types, the enum value is the intended
   one, an over-long body is shortened at a word boundary
   (the key phrase is early and survives), and for
   unknown_tool it falls back to the registered tool with
   the same argument shape (draft_reply -- a draft is not
   a send, and the lesson says so). For bad_id it first
   emits a search for the task's printed recovery query
   and retries with the id the search actually returns.
   Content -- which message, which label, what the draft
   says -- never changes (rule 1).

4. DETERMINISM. Same task in, same strings out, in every
   mode. The claims of the lesson are about the disposal
   machinery -- what each dispatcher does to the same
   proposals -- not about any provider you can buy.

Standard library only.
"""

import json

import tools

_LABEL_SYNONYMS = {"action": "act", "reply": "respond",
                   "fyi": "info", "archive": "file"}
_FILLER = (" Please treat this as time-sensitive and keep "
           "the whole thread in the loop.")


def _shorten(body, cap=500):
    if len(body) <= cap:
        return body
    cut = body[:cap].rsplit(" ", 1)[0]
    return cut.rstrip(",;")


def _mutate(spec):
    """The intended (name, args) with the value-level
    defects applied."""
    name = spec["name"]
    args = dict(spec["args"])
    defects = spec.get("defects", [])
    if "unknown_tool" in defects:
        name = spec["emitted_name"]
    if "type_string_int" in defects:
        for key, value in args.items():
            if isinstance(value, int) and not isinstance(value, bool):
                args[key] = str(value)
    if "missing_arg" in defects:
        args.pop(spec["missing_key"])
    if "extra_arg" in defects:
        args["confidence"] = 0.9
    if "enum_drift" in defects:
        args["label"] = _LABEL_SYNONYMS[args["label"]]
    if "bad_id" in defects:
        args["message_id"] = "rec-99"
    if "body_over" in defects:
        body = args["body"]
        while len(body) <= 500:
            body += _FILLER
        args["body"] = body
    return name, args


def emit(spec):
    """One intended call, serialised to the wire shape:
    {"name": ..., "arguments": "<a JSON string>"} -- with
    the call's string-level defects applied."""
    name, args = _mutate(spec)
    defects = spec.get("defects", [])
    if "args_single_quotes" in defects:
        text = repr(args)
    else:
        text = json.dumps(args)
        if "args_trailing" in defects:
            assert text.endswith("}")
            text = text[:-1] + ",}"
    return {"name": name, "arguments": text}


def correct(spec, store):
    """The correction emission(s) after the dispatcher's
    error result: the intended call, cleanly emitted (the
    registered fallback for an unknown tool; a search and
    then the retry, with the found id, for a bad id)."""
    defects = spec.get("defects", [])
    args = dict(spec["args"])
    if "body_over" in defects:
        args["body"] = _shorten(args["body"])
    if "bad_id" in defects:
        query = spec["recover_query"]
        hits = tools.execute(store, "search_inbox",
                             {"query": query, "max_results": 5})
        found = hits["hits"][0]["id"]
        search_spec = {"name": "search_inbox",
                       "args": {"query": query, "max_results": 5}}
        retry = {"name": spec["name"], "args": dict(args)}
        retry["args"]["message_id"] = found
        return [emit(search_spec), emit(retry)]
    name = spec["name"]
    if "unknown_tool" in defects:
        name = spec["fallback_tool"]
    return [emit({"name": name, "args": args})]


def plan_turns(task):
    """The task's intended turns: a list of turns, each a
    list of call specs."""
    return task["turns"]


def render_prompt(task, digest=""):
    """The prompt side of one model call, for pricing: the
    registry as handed to the model, the instruction, and
    the tool results so far."""
    return ("Tools:\n" + json.dumps(tools.render_registry())
            + "\n\nTask: " + task["instruction"]
            + ("\n\nResults so far:\n" + digest if digest else ""))
