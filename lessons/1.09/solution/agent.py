"""Disposal: what your code does with a proposed call.

Lesson AIE 1.09 -- Function Calling.

tool_lab.py models what the model proposes. This module is
the other half of the lesson: the code the proposals land
on. One per-call disposal, and three whole-run strategies
built from it, so the design space can be measured rather
than argued:

- dispatch(store, wire) -- the shipped disposal,
  agent@1.0.0. In order: the tool must be IN THE REGISTRY
  (a name outside it is refused, never executed); the
  arguments string must PARSE as JSON; the parsed
  arguments must VALIDATE against the tool's schema; only
  then does the call EXECUTE. Every failure is returned as
  an error result -- a code and the validator's located,
  named errors -- in the shape a tool result travels back
  to the model, so the model can correct the named defect
  and re-propose. A call gets at most MAX_CORRECTIONS
  corrections; a call that spends them fails its task,
  under its own name. Nothing unvalidated ever executes,
  and no refusal is silent.

- run_trust -- the found executor: parse what parses,
  execute what parses, no registry check, no validation.
  It is what most first integrations do. Its measurements
  are the lesson's argument: dropped calls, crashed tasks,
  and writes that land in the store in forms the schema
  forbids -- silently, because nothing ever looked.

- run_strict -- fail-fast: validate the whole turn before
  executing any of it; the first defective call refuses
  the task on the spot, with no feedback and no recovery.
  It never lands an invalid write. It also refuses tasks
  a feedback loop finishes in one correction -- safety
  bought with brittleness, priced in section 4 of
  run_tools.py.

The grading is the same for all three (grade()): the
store's end state against the task's gold -- labels
exactly, drafts by message and key phrase, and the gold
facts present in the tool results the run actually
returned. A run that completes with the wrong end state
on a task whose plan carries a planted judgement error is
graded "wrong": the ceiling every strategy shares.

Standard library only.
"""

import json

import tool_lab
import tools
from structured import price_call

MAX_CORRECTIONS = 2


# --------------------------------------------------------------- dispatch

def dispatch(store, wire):
    """agent@1.0.0's disposal of one proposed call. Returns
    a disposition: {"ok", "stage", "result"|"error"} where
    stage names where the call was disposed (registry,
    parse, validate, execute) -- the error surface is the
    interface the model corrects against."""
    name = wire["name"]
    if name not in tools.TOOL_SCHEMAS:
        return {"ok": False, "stage": "registry",
                "error": {"code": "UNKNOWN_TOOL",
                          "message": "{!r} is not in the registry; "
                                     "registered tools: {}".format(
                                         name, ", ".join(
                                             sorted(tools.TOOL_SCHEMAS)))}}
    try:
        args = json.loads(wire["arguments"])
    except (ValueError, TypeError):
        return {"ok": False, "stage": "parse",
                "error": {"code": "UNPARSEABLE_ARGUMENTS",
                          "message": "arguments is not valid JSON: "
                                     + wire["arguments"][:80]}}
    errors = tools.validate_args(name, args)
    if errors:
        return {"ok": False, "stage": "validate",
                "error": {"code": "INVALID_ARGUMENTS",
                          "message": "; ".join(errors)}}
    try:
        result = tools.execute(store, name, args)
    except tools.ToolError as exc:
        return {"ok": False, "stage": "execute",
                "error": {"code": exc.code, "message": exc.message}}
    return {"ok": True, "stage": "execute", "result": result}


# ------------------------------------------------------------------ runs

def _new_run(task, strategy):
    return {"task": task["id"], "strategy": strategy,
            "dispositions": [], "results": [], "model_calls": 0,
            "price": 0.0, "retries": 0, "invalid_executions": 0,
            "crashed": False, "refused": None, "failed_at": None,
            "executed": 0, "successful": 0}


def _emit_price(run, task, wires, digest):
    run["price"] += price_call(
        tool_lab.render_prompt(task, digest),
        json.dumps(wires))


def _digest(run):
    return json.dumps(run["results"])


def run_trust(task, store):
    """The found executor: parse-and-pray. No registry, no
    validation, no feedback; exceptions end the task."""
    run = _new_run(task, "trust")
    for turn in tool_lab.plan_turns(task):
        wires = [tool_lab.emit(spec) for spec in turn]
        run["model_calls"] += 1
        _emit_price(run, task, wires, _digest(run))
        for spec, wire in zip(turn, wires):
            try:
                args = json.loads(wire["arguments"])
            except (ValueError, TypeError):
                run["dispositions"].append(
                    {"name": wire["name"], "ok": False,
                     "stage": "parse", "detail": "dropped: "
                     "arguments unparseable, nobody told the model"})
                continue
            try:
                result = tools.execute(store, wire["name"], args)
            except Exception as exc:  # the executor dies with the task
                run["dispositions"].append(
                    {"name": wire["name"], "ok": False,
                     "stage": "execute",
                     "detail": "CRASH: {!r}".format(exc)})
                run["crashed"] = True
                return run
            run["executed"] += 1
            valid = not tools.validate_args(wire["name"], args)
            if valid:
                run["successful"] += 1
            elif tools.TOOL_SCHEMAS.get(wire["name"], {}).get(
                    "access") == "write":
                run["invalid_executions"] += 1
            run["results"].append(result)
            run["dispositions"].append(
                {"name": wire["name"], "ok": True, "stage": "execute",
                 "detail": "executed (never validated)"})
    return run


def run_strict(task, store):
    """Fail-fast: the whole turn validates before any of it
    executes; the first defect refuses the task."""
    run = _new_run(task, "strict")
    for turn in tool_lab.plan_turns(task):
        wires = [tool_lab.emit(spec) for spec in turn]
        run["model_calls"] += 1
        _emit_price(run, task, wires, _digest(run))
        defect = None
        parsed = []
        for wire in wires:
            if wire["name"] not in tools.TOOL_SCHEMAS:
                defect = ("registry", wire["name"],
                          "unknown tool")
                break
            try:
                args = json.loads(wire["arguments"])
            except (ValueError, TypeError):
                defect = ("parse", wire["name"],
                          "arguments unparseable")
                break
            errors = tools.validate_args(wire["name"], args)
            if errors:
                defect = ("validate", wire["name"], errors[0])
                break
            parsed.append(args)
        if defect:
            run["refused"] = defect
            run["dispositions"].append(
                {"name": defect[1], "ok": False, "stage": defect[0],
                 "detail": "task refused: " + defect[2]})
            return run
        for wire, args in zip(wires, parsed):
            try:
                result = tools.execute(store, wire["name"], args)
            except tools.ToolError as exc:
                run["refused"] = ("execute", wire["name"],
                                   "{}: {}".format(exc.code,
                                                   exc.message))
                run["dispositions"].append(
                    {"name": wire["name"], "ok": False,
                     "stage": "execute",
                     "detail": "task aborted: " + exc.message})
                return run
            run["executed"] += 1
            run["successful"] += 1
            run["results"].append(result)
            run["dispositions"].append(
                {"name": wire["name"], "ok": True, "stage": "execute",
                 "detail": "executed (validated)"})
    return run


def _agent_call(task, store, spec, run):
    wire = tool_lab.emit(spec)
    used = 0
    while True:
        disp = dispatch(store, wire)
        run["dispositions"].append(
            {"name": wire["name"], "ok": disp["ok"],
             "stage": disp["stage"],
             "detail": "executed" if disp["ok"] else
             "{}: {}".format(disp["error"]["code"],
                             disp["error"]["message"])})
        if disp["ok"]:
            run["executed"] += 1
            run["successful"] += 1
            run["results"].append(disp["result"])
            return True
        if used >= MAX_CORRECTIONS:
            run["failed_at"] = {"name": wire["name"],
                                "error": disp["error"]}
            return False
        used += 1
        run["retries"] += 1
        wires = tool_lab.correct(spec, store)
        for w in wires:
            run["model_calls"] += 1
            _emit_price(run, task, [w], _digest(run))
        for w in wires[:-1]:  # recovery calls (the bad-id search)
            d2 = dispatch(store, w)
            run["dispositions"].append(
                {"name": w["name"], "ok": d2["ok"],
                 "stage": d2["stage"],
                 "detail": "recovery call"})
            if d2["ok"]:
                run["executed"] += 1
                run["successful"] += 1
                run["results"].append(d2["result"])
        wire = wires[-1]


def run_agent(task, store):
    """agent@1.0.0: dispatch with the error-feedback loop."""
    run = _new_run(task, "agent")
    for turn in tool_lab.plan_turns(task):
        wires = [tool_lab.emit(spec) for spec in turn]
        run["model_calls"] += 1
        _emit_price(run, task, wires, _digest(run))
        for spec in turn:
            if not _agent_call(task, store, spec, run):
                return run
    return run


RUNNERS = {"trust": run_trust, "strict": run_strict,
           "agent": run_agent}


# --------------------------------------------------------------- grading

def grade(task, store, run):
    """Grade one finished run against the task's gold.
    Returns "correct", "wrong" (completed; the end state
    differs -- on a judgement task, by the planted error),
    or "failed" (crashed, refused, or incomplete)."""
    gold = task["gold"]
    labels_ok = store.labels == gold.get("labels", {})
    drafts_ok = True
    gold_drafts = gold.get("drafts", [])
    if len(store.drafts) != len(gold_drafts):
        drafts_ok = False
    else:
        for want in gold_drafts:
            if not any(d["message_id"] == want["message_id"]
                       and want["body_key"] in d["body"]
                       for d in store.drafts):
                drafts_ok = False
    digest = _digest(run)
    facts_ok = all(f in digest for f in gold.get("facts", []))
    completed = (not run["crashed"] and run["refused"] is None
                 and run["failed_at"] is None
                 and run["successful"] >= _planned_calls(task))
    if labels_ok and drafts_ok and facts_ok:
        return "correct"
    if completed:
        return "wrong"
    return "failed"


def _planned_calls(task):
    return sum(len(turn) for turn in task["turns"])


def first_emission_census(tasks):
    """Classify every planned call's FIRST emission, before
    any strategy touches it: clean, or defective -- and how.
    A bad_id call is formally clean (it parses and
    validates); it is wrong in the world, and counted
    apart."""
    census = {"clean": 0, "world": 0}
    total = 0
    for task in tasks:
        for turn in task["turns"]:
            for spec in turn:
                total += 1
                wire = tool_lab.emit(spec)
                defects = [d for d in spec.get("defects", [])
                           if d != "bad_id"]
                if "bad_id" in spec.get("defects", []):
                    census["world"] += 1
                if not defects:
                    census["clean"] += 1
                for d in defects:
                    census[d] = census.get(d, 0) + 1
    census["total"] = total
    census["defective"] = total - census["clean"]
    return census
