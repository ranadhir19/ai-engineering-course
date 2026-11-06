"""The worked solution for Exercise 1.09.

Built on the lesson's shipped machinery: the registry
and validator from ../solution/tools.py -- the same
schemas agent@1.0.0 validates against. Offline, there is
no model to hand errors back to, so the feedback loop is
replaced by its honest static form:

- EVERY call is validated before ANY call executes
  (registry, parse, schema) -- a turn is disposed as a
  whole, so nothing lands half-checked.
- Calls that validate are executed in order; an
  execution error (a message id the world does not have)
  is recorded as that call's result, not raised -- the
  remaining calls still dispose on their own merits.
- Calls that do not validate are refused, by name, with
  the validator's located errors as the reason. Refusal
  is priced against completion, exactly as the bars
  intend: six of the sixteen tasks cannot be completed
  honestly, and no dispatcher may complete them by
  guessing (coercing a drifted enum, inventing a missing
  argument, substituting a tool the registry lacks).
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "..", "..", "solution"))

import tools  # noqa: E402


def run_task(calls, store):
    log = {"results": [], "refused": []}
    # Phase 1: validate everything, execute nothing yet.
    parsed = []
    for wire in calls:
        if wire["name"] not in tools.TOOL_SCHEMAS:
            log["refused"].append(
                (wire["name"], "unknown tool (not in the registry)"))
            parsed.append(None)
            continue
        try:
            args = json.loads(wire["arguments"])
        except (ValueError, TypeError):
            log["refused"].append(
                (wire["name"], "arguments unparseable as JSON"))
            parsed.append(None)
            continue
        errors = tools.validate_args(wire["name"], args)
        if errors:
            log["refused"].append((wire["name"], errors[0]))
            parsed.append(None)
            continue
        parsed.append((wire["name"], args))
    # Phase 2: execute the valid calls, in order.
    for item in parsed:
        if item is None:
            continue
        name, args = item
        try:
            result = tools.execute(store, name, args)
        except tools.ToolError as exc:
            log["results"].append(
                {"error": {"code": exc.code, "message": exc.message}})
            continue
        log["results"].append(result)
    return log
