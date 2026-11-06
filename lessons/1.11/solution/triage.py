"""Triage: the Inbox Assistant's new job, done through the library.

Lesson AIE 1.05 -- Prompt Engineering.

``triage`` renders the versioned triage template, sends the messages
to a model backend, and parses the completion the way downstream
code has to: strictly. The completion, stripped, must BE one of the
four labels -- a sentence that merely mentions a label is a parse
failure, and it raises TriageParseError rather than being quietly
interpreted. (That strictness is the whole lesson: it is what the
failing prompt, triage@0.1.0, cannot survive, at 0 of 20 cases.)

The default backend is this lesson's stand-in, prompt_lab.respond.
Any callable taking a message list and returning a string can be
injected -- the interface is the one every lesson has used: messages
in, completion out.

Standard library only.
"""

import prompt_lab
import prompts

LABELS = prompts.LABELS


class TriageParseError(Exception):
    """The completion was not exactly one label. Carries the raw
    completion so the failure can be inspected, never swallowed."""


def parse_label(completion):
    """Strict parse: the stripped completion must be a label."""
    label = completion.strip().lower()
    if label not in LABELS:
        raise TriageParseError(
            "completion is not exactly one label: " + repr(completion))
    return label


def mentioned_label(completion):
    """Diagnostic only: which label (or known synonym) a completion
    mentions, if any. Used by the drivers to report what a prompt's
    answers *say*, separately from what a parser can *use*."""
    text = completion.lower()
    for label in LABELS + ("urgent", "read-later", "bin"):
        if label in text:
            return label
    return None


def triage(email_text, version=None, backend=None):
    """One email in, one label out -- or a named error."""
    if backend is None:
        backend = prompt_lab.respond
    messages = prompts.render("triage", version, email=email_text)
    return parse_label(backend(messages))
