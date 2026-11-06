"""The failing prompt, packaged as found. THIS IS THE EXERCISE.

Lesson AIE 1.05 exercise starter.

``build_messages`` below is the prompt the Assistant's triage job
was shipped with: one cheerful sentence and the raw email. Against
the 20-case test set it scores 0 of 20 under the strict parse the
downstream code performs -- not because the model cannot classify
(it names the right label in 12 cases), but because nothing it says
can be consumed: prose answers, private synonyms for labels, and
instructions written inside emails are obeyed.

Your task is in README.md in this folder: rebuild build_messages
until the harness reports 18 of 20 or better, and document the
failures that remain.
"""


def build_messages(email_text):
    """One email in, the message list to send. Edit this function."""
    return [
        {"role": "user", "content": "Triage this email for me.\n\n" + email_text},
    ]
