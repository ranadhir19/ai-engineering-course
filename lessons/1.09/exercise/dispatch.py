"""The found dispatcher for Exercise 1.09 -- execute on trust.

This is the dispatcher as it exists wherever a model's
tool calls are first wired up: take the call, parse the
arguments string, hand both to the function. It works on
the calls that were never broken. On the rest it does one
of three things, all bad: it drops the call silently (the
task just never happens), it crashes (an exception nobody
translated, and the rest of the task dies with it), or --
worst -- it executes, landing a write in the store in a
form the tool's own signature forbids.

Your exercise is to replace it: a dispatcher that
validates every call against the registry before
executing any of them, executes the valid ones, records
execution errors as results instead of dying on them, and
refuses the invalid ones by name. The bars are in
README.md; the harness grades this module against them:

    python3 tools_harness.py --dispatcher dispatch.py

The interface is the contract: run_task(calls, store)
takes the task's proposed calls as data (wire dicts:
{"name": ..., "arguments": "<json string>"}) and a
tools.Store, disposes them, and returns a log dict with
at least "results" (the tool results returned) and
"refused" (a list of (name, reason) for the calls it
refused).
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "..", "solution"))

import tools  # noqa: E402


def run_task(calls, store):
    """Trust, as a function: parse the arguments, execute
    the call, hope."""
    log = {"results": [], "refused": []}
    for wire in calls:
        try:
            args = json.loads(wire["arguments"])
        except (ValueError, TypeError):
            continue  # dropped -- silently, like production
        result = tools.execute(store, wire["name"], args)
        log["results"].append(result)
    return log
