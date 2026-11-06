"""Exercise 1.07 starter -- the sampling settings, as found.

This file is the whole surface of the exercise: the SETTINGS
the Assistant's calls currently run at. They are the provider
default, inherited without a decision -- one global temperature
of 1.0, no candidate filters, one draw, for a triage filer, a
rubric grader and a brainstorming tool alike, as if variance
meant the same thing to all three.

Your task (exercise/README.md): choose a setting per task --
temperature, top_k, top_p, vote_k -- until sampling_harness.py
reports every bar met. The lab (../solution/sampling_lab.py),
the suites (tasks.json) and the measurement code
(../solution/sampling.py) are not yours to edit: the dials are
the deliverable, and the defence of each setting is the lesson.
"""

# The settings, as found: one global default for everything.
SETTINGS = {
    "extraction": {"temperature": 1.0, "top_k": None,
                   "top_p": None, "vote_k": 1},
    "grading": {"temperature": 1.0, "top_k": None,
                "top_p": None, "vote_k": 1},
    "brainstorming": {"temperature": 1.0, "top_k": None,
                      "top_p": None, "vote_k": 1},
}
