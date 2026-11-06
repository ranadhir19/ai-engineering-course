"""Repository harness for ai-engineering-course.

Run from anywhere:
    python3 validate.py

Checks:
  1. Every .py file in the repository compiles (py_compile).
  2. The lesson 1.01 failure harness passes against the exercise
     solution client (its default target).
  3. The lesson 1.02 routing harness passes against the exercise
     solution router (its default target).
  4. The lesson 1.03 budget harness passes against the exercise
     solution budget (its default target).
  5. The lesson 1.04 stream harness passes against the exercise
     solution streaming (its default target).
  6. The lesson 1.05 prompt harness passes against the exercise
     solution prompts (its default target).
  7. The lesson 1.06 context harness passes against the exercise
     solution assembler (its default target).
  8. The lesson 1.07 sampling harness passes against the exercise
     solution settings (its default target).
  9. The lesson 1.08 records harness passes against the exercise
     solution extractor (its default target).
 10. The lesson 1.09 tools harness passes against the exercise
     solution dispatcher (its default target).
 11. Every existing lesson folder has starter/, solution/, exercise/
     and a README.md.

Prints PASS/FAIL per check and exits non-zero on any failure.
Standard library only.
"""

import os
import py_compile
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FAILURES = []


def report(ok, label, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ((" -- " + detail) if detail else ""))
    if not ok:
        FAILURES.append(label)


def check_compile():
    py_files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git", ".venv")]
        for name in sorted(filenames):
            if name.endswith(".py"):
                py_files.append(os.path.join(dirpath, name))
    bad = []
    for path in py_files:
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as exc:
            bad.append(os.path.relpath(path, ROOT) + ": " + str(exc))
    report(not bad, "py_compile all .py files (" + str(len(py_files)) + " files)", "; ".join(bad))


def check_harness():
    harness = os.path.join(ROOT, "lessons", "1.01", "exercise", "failure_harness.py")
    if not os.path.isfile(harness):
        report(False, "lesson 1.01 failure harness", "missing: " + harness)
        return
    result = subprocess.run(
        [sys.executable, harness],
        capture_output=True,
        text=True,
        timeout=300,
    )
    tail = (result.stdout.strip().splitlines() or [""])[-1]
    report(
        result.returncode == 0,
        "lessons/1.01 exercise failure_harness (exercise solution client)",
        "exit=" + str(result.returncode) + " " + tail,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)


def check_harness_102():
    harness = os.path.join(ROOT, "lessons", "1.02", "exercise", "router_harness.py")
    if not os.path.isfile(harness):
        report(False, "lesson 1.02 routing harness", "missing: " + harness)
        return
    result = subprocess.run(
        [sys.executable, harness],
        capture_output=True,
        text=True,
        timeout=300,
    )
    tail = (result.stdout.strip().splitlines() or [""])[-1]
    report(
        result.returncode == 0,
        "lessons/1.02 exercise router_harness (exercise solution router)",
        "exit=" + str(result.returncode) + " " + tail,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)


def check_harness_103():
    harness = os.path.join(ROOT, "lessons", "1.03", "exercise", "budget_harness.py")
    if not os.path.isfile(harness):
        report(False, "lesson 1.03 budget harness", "missing: " + harness)
        return
    result = subprocess.run(
        [sys.executable, harness],
        capture_output=True,
        text=True,
        timeout=600,
    )
    tail = (result.stdout.strip().splitlines() or [""])[-1]
    report(
        result.returncode == 0,
        "lessons/1.03 exercise budget_harness (exercise solution budget)",
        "exit=" + str(result.returncode) + " " + tail,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)


def check_harness_104():
    harness = os.path.join(ROOT, "lessons", "1.04", "exercise", "stream_harness.py")
    if not os.path.isfile(harness):
        report(False, "lesson 1.04 stream harness", "missing: " + harness)
        return
    result = subprocess.run(
        [sys.executable, harness],
        capture_output=True,
        text=True,
        timeout=600,
    )
    tail = (result.stdout.strip().splitlines() or [""])[-1]
    report(
        result.returncode == 0,
        "lessons/1.04 exercise stream_harness (exercise solution streaming)",
        "exit=" + str(result.returncode) + " " + tail,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)


def check_harness_105():
    harness = os.path.join(ROOT, "lessons", "1.05", "exercise", "prompt_harness.py")
    if not os.path.isfile(harness):
        report(False, "lesson 1.05 prompt harness", "missing: " + harness)
        return
    result = subprocess.run(
        [sys.executable, harness],
        capture_output=True,
        text=True,
        timeout=300,
    )
    tail = (result.stdout.strip().splitlines() or [""])[-1]
    report(
        result.returncode == 0,
        "lessons/1.05 exercise prompt_harness (exercise solution prompts)",
        "exit=" + str(result.returncode) + " " + tail,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)


def check_harness_106():
    harness = os.path.join(ROOT, "lessons", "1.06", "exercise", "context_harness.py")
    if not os.path.isfile(harness):
        report(False, "lesson 1.06 context harness", "missing: " + harness)
        return
    result = subprocess.run(
        [sys.executable, harness],
        capture_output=True,
        text=True,
        timeout=300,
    )
    tail = (result.stdout.strip().splitlines() or [""])[-1]
    report(
        result.returncode == 0,
        "lessons/1.06 exercise context_harness (exercise solution assembler)",
        "exit=" + str(result.returncode) + " " + tail,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)


def check_harness_107():
    harness = os.path.join(ROOT, "lessons", "1.07", "exercise", "sampling_harness.py")
    if not os.path.isfile(harness):
        report(False, "lesson 1.07 sampling harness", "missing: " + harness)
        return
    result = subprocess.run(
        [sys.executable, harness],
        capture_output=True,
        text=True,
        timeout=300,
    )
    tail = (result.stdout.strip().splitlines() or [""])[-1]
    report(
        result.returncode == 0,
        "lessons/1.07 exercise sampling_harness (exercise solution settings)",
        "exit=" + str(result.returncode) + " " + tail,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)


def check_harness_108():
    harness = os.path.join(ROOT, "lessons", "1.08", "exercise", "records_harness.py")
    if not os.path.isfile(harness):
        report(False, "lesson 1.08 records harness", "missing: " + harness)
        return
    result = subprocess.run(
        [sys.executable, harness],
        capture_output=True,
        text=True,
        timeout=300,
    )
    tail = (result.stdout.strip().splitlines() or [""])[-1]
    report(
        result.returncode == 0,
        "lessons/1.08 exercise records_harness (exercise solution extractor)",
        "exit=" + str(result.returncode) + " " + tail,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)


def check_harness_109():
    harness = os.path.join(ROOT, "lessons", "1.09", "exercise", "tools_harness.py")
    if not os.path.isfile(harness):
        report(False, "lesson 1.09 tools harness", "missing: " + harness)
        return
    result = subprocess.run(
        [sys.executable, harness],
        capture_output=True,
        text=True,
        timeout=300,
    )
    tail = (result.stdout.strip().splitlines() or [""])[-1]
    report(
        result.returncode == 0,
        "lessons/1.09 exercise tools_harness (exercise solution dispatcher)",
        "exit=" + str(result.returncode) + " " + tail,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)


def check_lesson_structure():
    lessons_dir = os.path.join(ROOT, "lessons")
    lesson_folders = []
    if os.path.isdir(lessons_dir):
        for name in sorted(os.listdir(lessons_dir)):
            path = os.path.join(lessons_dir, name)
            if os.path.isdir(path):
                lesson_folders.append((name, path))
    if not lesson_folders:
        report(False, "lesson folder structure", "no lesson folders found")
        return
    for name, path in lesson_folders:
        missing = []
        for sub in ("starter", "solution", "exercise"):
            if not os.path.isdir(os.path.join(path, sub)):
                missing.append(sub + "/")
        if not os.path.isfile(os.path.join(path, "README.md")):
            missing.append("README.md")
        report(
            not missing,
            "lessons/" + name + " structure (starter/, solution/, exercise/, README.md)",
            ("missing: " + ", ".join(missing)) if missing else "",
        )


def main():
    check_compile()
    check_harness()
    check_harness_102()
    check_harness_103()
    check_harness_104()
    check_harness_105()
    check_harness_106()
    check_harness_107()
    check_harness_108()
    check_harness_109()
    check_lesson_structure()
    if FAILURES:
        print("OVERALL: FAIL (" + str(len(FAILURES)) + " check(s) failed)")
        return 1
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
