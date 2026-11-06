"""The measurements for Lesson 1.05, in five sections.

    python3 run_prompts.py            # all sections
    python3 run_prompts.py ladder     # or one at a time:
                                      # ladder | library | cost |
                                      # guard | thread

Everything runs against this lesson's stand-in model (prompt_lab),
which is deterministic: these numbers reproduce exactly, every run.
Scores are STRICT: a case passes only if the completion, stripped,
is exactly the gold label -- the parse the Assistant's downstream
code performs. A second number, MENTIONED, counts the cases whose
completion names the gold label (or, for the failing prompt, fails
to): the gap between the two is the price of prose.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import prompt_lab
import prompts
import triage as triage_mod
from tokenizer import count_tokens

with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as f:
    CASES = json.load(f)["cases"]

VERSIONS = ["0.1.0", "0.2.0", "0.3.0", "1.0.0", "1.1.0"]
ATLAS_IN, ATLAS_OUT = 0.80, 1.60  # dollars per million tokens (1.02)


def _words(messages_or_text):
    if isinstance(messages_or_text, str):
        return len(messages_or_text.split())
    return sum(len(str(m.get("content", "")).split())
               for m in messages_or_text)


def run_version(version):
    """(strict_passes, mentioned, per-case rows) for one version."""
    rows = []
    strict = mentioned = 0
    for case in CASES:
        messages = prompts.render("triage", version, email=case["email"])
        completion = prompt_lab.respond(messages)
        said = completion.strip().lower()
        ok = said == case["gold"]
        names = triage_mod.mentioned_label(completion)
        if ok:
            strict += 1
        if names == case["gold"]:
            mentioned += 1
        rows.append((case, ok, said if ok else (names or said)))
    return strict, mentioned, rows


def section_ladder():
    print("== the ladder: one change at a time, 20 cases, strict parse ==")
    prev_fails = None
    for version in VERSIONS[:-1]:
        strict, mentioned, rows = run_version(version)
        fails = [c["id"] for c, ok, _ in rows if not ok]
        fixed = ""
        if prev_fails is not None:
            newly = [i for i in prev_fails if i not in fails]
            fixed = "  fixed: " + (", ".join(map(str, newly)) or "none")
        print("triage@%-6s strict %2d/20   mentioned %2d/20   "
              "failing: %s%s"
              % (version, strict, mentioned,
                 ", ".join(map(str, fails)) or "none", fixed))
        prev_fails = fails
    print("the failing prompt (0.1.0) names the right label in 12 "
          "cases —\nand a parser can use none of them. prose is not "
          "an interface.")


def section_library():
    print("== the library: a prompt fix shipped like a code fix ==")
    _, _, rows_100 = run_version("1.0.0")
    strict_110, _, rows_110 = run_version("1.1.0")
    fails_100 = {c["id"]: said for c, ok, said in rows_100 if not ok}
    print("triage@1.0.0 regression-pinned at %d/20; failing: %s"
          % (20 - len(fails_100),
             ", ".join("case %d (said %s)" % kv
                       for kv in fails_100.items()) or "none"))
    moved = []
    for (c1, ok1, _), (c2, ok2, _) in zip(rows_100, rows_110):
        if ok1 != ok2:
            moved.append((c1["id"], ok1, ok2))
    print("triage@1.1.0 = 1.0.0 + one worked example (convention C3)")
    print("score %d/20; cases whose verdict changed: %s"
          % (strict_110,
             ", ".join("case %d %s->%s" % (i, "PASS" if a else "FAIL",
                                           "PASS" if b else "FAIL")
                       for i, a, b in moved) or "none"))
    regressions = [i for i, a, b in moved if a and not b]
    print("regressions: %s" % (", ".join(map(str, regressions)) or "none"))
    for version, note in prompts.changelog("triage"):
        print("  %-6s %s" % (version, note))


def section_cost():
    print("== the price of accuracy: the whole 20-case suite, "
          "atlas prices ==")
    print("prompt words are the servers' meter (whitespace words); "
          "cost at\n$0.80 in / $1.60 out per million.")
    for version in VERSIONS:
        in_words = out_words = 0
        for case in CASES:
            messages = prompts.render("triage", version,
                                      email=case["email"])
            completion = prompt_lab.respond(messages)
            in_words += _words(messages)
            out_words += _words(completion)
        cost = (in_words * ATLAS_IN + out_words * ATLAS_OUT) / 1_000_000
        print("triage@%-6s suite: %5d words in, %4d words out, "
              "$%.6f" % (version, in_words, out_words, cost))
    messages = prompts.render("triage", "1.1.0", email=CASES[0]["email"])
    text = " ".join(m["content"] for m in messages)
    print("two meters on triage@1.1.0, case 1: %d words by the "
          "servers' meter,\n%d tokens by 1.03's BPE counter — the "
          "prompt is the biggest input the Assistant sends."
          % (_words(messages), count_tokens(text)))


def section_guard():
    print("== the render guard: checked before anything is sent ==")
    calls = []

    def counting_backend(messages):
        calls.append(messages)
        return prompt_lab.respond(messages)

    try:
        prompts.render("triage", "1.1.0")
        print("ERROR: render without inputs did not raise")
    except prompts.MissingInputError as exc:
        print("render(triage@1.1.0) with no email -> MissingInputError:")
        print("  " + str(exc))
    try:
        prompts.render("triage", "9.9.9", email="x")
    except prompts.UnknownTemplateError as exc:
        print("render(triage@9.9.9) -> UnknownTemplateError (named, "
              "listed)")
    label = triage_mod.triage(CASES[0]["email"], version="1.1.0",
                              backend=counting_backend)
    print("with the input supplied: label %r after %d model call(s)"
          % (label, len(calls)))


def section_thread():
    print("== the thread: the Assistant files its own inbox ==")
    from mock_provider_server import EMAILS
    for email in EMAILS:
        text = ("From: Inbox\nSubject: " + email["subject"] + "\n\n"
                + " ".join(email["sentences"]))
        label = triage_mod.triage(text, version="1.1.0")
        print("  %-42s -> %s" % (email["subject"], label))
    print("three announcements, three fyi — filed by the template "
          "the test\nset certified, at the version the changelog "
          "records.")


SECTIONS = {"ladder": section_ladder, "library": section_library,
            "cost": section_cost, "guard": section_guard,
            "thread": section_thread}


def main():
    names = sys.argv[1:] or list(SECTIONS)
    for name in names:
        SECTIONS[name]()
        print()


if __name__ == "__main__":
    main()
