"""The 20-case prompt harness for Exercise 1.05.

    python3 prompt_harness.py                      # grade the worked solution
    python3 prompt_harness.py --prompts prompts.py # grade the starter (0/20)

Loads the module under test (it must define build_messages(email)),
runs every case in cases.json through this lesson's stand-in model
(../solution/prompt_lab.py -- deterministic, so the score you see is
the score there is), and grades STRICTLY: a case passes only if the
completion, stripped, is exactly the gold label. That is the parse
the Assistant's downstream code performs; a completion that merely
mentions the right label in prose is a failure, and the report says
what it said instead.

Pass mark (from the lesson, stated before any code): 18 of 20 or
better, with the remaining failures documented. Exit 0 at the pass
mark, 1 below it.
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SOLUTION = os.path.join(HERE, "..", "solution")
sys.path.insert(0, SOLUTION)

import prompt_lab  # noqa: E402

PASS_MARK = 18


def load_module(path):
    spec = importlib.util.spec_from_file_location("prompts_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description="Exercise 1.05 prompt harness.")
    parser.add_argument(
        "--prompts",
        default=os.path.join(HERE, "solution", "prompts.py"),
        help="module under test (default: the worked solution)",
    )
    args = parser.parse_args()
    module = load_module(args.prompts)
    with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    print("prompts module under test: " + args.prompts)
    passed = 0
    for case in cases:
        messages = module.build_messages(case["email"])
        completion = prompt_lab.respond(messages)
        said = completion.strip().lower()
        ok = said == case["gold"]
        if ok:
            passed += 1
        print(
            "%s %2d %-10s gold=%-7s said=%s"
            % ("PASS" if ok else "FAIL", case["id"], case["family"],
               case["gold"], said if ok else repr(completion.strip()[:64]))
        )
    print("RESULT: %d/%d cases passed (pass mark %d)"
          % (passed, len(cases), PASS_MARK))
    return 0 if passed >= PASS_MARK else 1


if __name__ == "__main__":
    sys.exit(main())
