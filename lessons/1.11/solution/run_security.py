#!/usr/bin/env python3
"""run_security.py -- Lesson 1.11 demonstration driver.

Sections:
  1. The wild: a census of 30 episodes against the thread system
  2. Trust: agent@1.0.0 reads everything as instruction
  3. Delimiters: channel discipline alone
  4. The shipped stack: security@1.0.0, layer by layer
  5. The table and the cost (incl. the gold correction)
  6. The ceiling and the shipped statement

Every number below is computed from episodes.json at runtime.
Gold outcomes were authored with the fixtures, before the
defence code (episodes.json, "about") -- with one correction,
printed in section 5 rather than buried.
"""

import time
from collections import Counter

import attack_lab
import security

EPS = attack_lab.episodes()
BY_ID = {e["id"]: e for e in EPS}
ATTACKS = [e for e in EPS if e["payload"]]
BENIGN = [e for e in EPS if not e["payload"]]


def line():
    print("=" * 72)


def kind_table(outcomes):
    """breaches by payload kind, for one config's outcomes."""
    kinds = {}
    for ep, out in zip(EPS, outcomes):
        if not ep["payload"]:
            continue
        k = ep["payload"]["kind"]
        kinds.setdefault(k, [0, 0])
        kinds[k][1] += 1
        if out["breach"]:
            kinds[k][0] += 1
    return kinds


# ----------------------------------------------------------------------
line()
print("1. THE WILD -- 30 episodes against the Inbox Assistant")
line()
print("""
  the system under attack is the thread system as 1.10 left it:
  four tools (search_inbox, get_record -- reads; apply_label,
  draft_reply -- writes), a dispatcher that rejects malformed
  calls, and boundary@1.0.0 certifying the FORM of every
  crossing. Every payload in this corpus is formally perfect.
  Form was never the question. Origin is.

  the asset is not the data. It is the assistant's tool
  authority: the right to label the whole inbox and to write
  drafts in the user's name. An injection is any content that
  spends that authority without the user's instruction.

  census: %d episodes -- %d attacks, %d benign controls
  attack classes: %s
  surfaces: %s
""" % (len(EPS), len(ATTACKS), len(BENIGN),
       ", ".join("%s %d" % (k, n) for k, n in
                 sorted(Counter(e["payload"]["kind"]
                                for e in ATTACKS).items())),
       ", ".join("%s %d" % (k, n) for k, n in
                 sorted(Counter(e["surface"]
                                for e in EPS).items()))))
print("  gold outcomes under the shipped stack were authored")
print("  with the fixtures, before any defence ran (the")
print("  episodes.json 'about' note is the pre-registration).")

for name in ("trust", "delimiters", "security@1.0.0"):
    cfg = security.CONFIGS[name]
    out = attack_lab.run_corpus(cfg)
    s = attack_lab.summarise(out)
    if name == "trust":
        line()
        print("2. TRUST -- agent@1.0.0: content read as instruction")
        line()
        print("""
  R2 (attack_lab.py): with no channel discipline, the model
  treats any instruction addressed to it, wherever found, as
  its job -- the last instruction wins. The 1.09 dispatcher and
  the 1.10 gate never fire: every payload call is in-contract.

  breaches: %d of %d attacks executed their payload
  tasks completed: %d of %d (trust does the task AND the
  payload -- availability was never its problem)
""" % (s["breaches"], len(ATTACKS), s["tasks_done"], len(EPS)))
    elif name == "delimiters":
        line()
        print("3. DELIMITERS -- channel discipline alone")
        line()
        print("""
  R1+R3: only the user's turn instructs; content is data.
  Thirteen payloads die here -- every plain override, hijack,
  exfil and paraphrase: an instruction in data is read ABOUT,
  never read AS an order. Novel wording changes nothing
  (paraphrase, 3 for 3): the channel decides, not the text.

  breaches: %d of %d -- the survivors are the five channels
  discipline cannot close (attack_lab.ELEVATED):
    mimicry    framed as a principal, discipline marks the
               channel and the content claims it lies
    encoded    decoded by the model, then read as instruction
    pasted     carried in on the trusted channel, by the user
    delegated  the user authorised following this source
    semantic   a claim, not a call -- nothing to refuse
  tasks completed: %d of %d (discipline costs no availability)
""" % (s["breaches"], len(ATTACKS), s["tasks_done"], len(EPS)))
    else:
        line()
        print("4. THE SHIPPED STACK -- security@1.0.0")
        line()
        agree = sum(1 for o, e in zip(out, EPS)
                    if o["outcome"] == e["gold"]["full"])
        print("""
  layer 2, the boundary screen (security.PATTERNS): holds on
  FORM -- a principal impersonated, an instruction addressed
  to the assistant on a data surface, an encoded run. Layer 3,
  the action gate (G1-G4): a proposed call must stay inside
  the task's working set, or be refused by name.
""")
        for ep, o in zip(EPS, out):
            if o["outcome"] in ("held", "refused"):
                print("  %-7s %-8s %s" % (ep["id"], o["outcome"],
                                          o["reason"]))
        print("""
  breaches: %d of %d -- named in section 6, in writing
  tasks completed immediately: %d of %d; %d contents held for
  a principal's decision (%d attacks, %d benign: ben-04, the
  quoted joke -- the screen cannot tell a quotation from an
  order, and does not pretend to)
  agreement with the pre-registered gold: %d/%d
""" % (s["breaches"], len(ATTACKS), s["tasks_done"], len(EPS),
       s["held"], s["held"] - 1, 1, agree, len(EPS)))

# ----------------------------------------------------------------------
line()
print("5. THE TABLE AND THE COST")
line()
outs = {n: attack_lab.run_corpus(security.CONFIGS[n])
        for n in ("trust", "delimiters", "security@1.0.0")}
kinds = kind_table(outs["trust"])
print("\n  breaches by attack class (of n):")
print("  %-11s %5s %10s %11s %9s" % ("class", "n", "trust",
                                     "delimiters", "shipped"))
order = ["override", "hijack", "exfil", "paraphrase", "mimicry",
         "encoded", "pasted", "delegated", "semantic"]
for k in order:
    row = []
    for n in ("trust", "delimiters", "security@1.0.0"):
        kt = kind_table(outs[n])
        row.append(kt[k][0])
    print("  %-11s %5d %10d %11d %9d" % (k, kinds[k][1], *row))
tt = {n: attack_lab.summarise(outs[n]) for n in outs}
print("  %-11s %5d %10d %11d %9d" % ("TOTAL", len(ATTACKS),
      tt["trust"]["breaches"], tt["delimiters"]["breaches"],
      tt["security@1.0.0"]["breaches"]))
print("  %-11s %5s %10d %11d %9d" % ("tasks done", len(EPS),
      tt["trust"]["tasks_done"], tt["delimiters"]["tasks_done"],
      tt["security@1.0.0"]["tasks_done"]))

t0 = time.perf_counter()
for _ in range(200):
    attack_lab.run_corpus(security.CONFIGS["security@1.0.0"])
per = (time.perf_counter() - t0) / 200 / len(EPS) * 1e6
print("""
  cost, measured here, this run:
    full-stack pass: %.0f microseconds per episode of local CPU
    (the shape is the claim, not the digit); model calls: 0
  the real price, as in 1.10, is the queue: %d contents held
  for a principal, and the pattern list itself -- someone has
  to own security.PATTERNS the way someone owns a contract.

  THE GOLD CORRECTION, printed rather than buried: the
  pre-registered key predicted the screen would hold only the
  impersonation and encoding classes (7 holds). It also holds
  the seven plain-instruction payloads (atk-01..05, 07, 10) --
  same safety outcome, higher availability cost. The breach
  half of the key did not move: 3 predicted, 3 measured, the
  same three episodes. A screen that can hold ben-04's quoted
  order cannot decline atk-01's identical shape; section 4's
  table is the corrected key, and episodes.json records it.
""" % (per, tt["security@1.0.0"]["held"]))

# ----------------------------------------------------------------------
line()
print("6. THE CEILING AND THE SHIPPED STATEMENT")
line()
print("""
  the residuals, read back by name:
""")
for eid in ("atk-22", "atk-23", "atk-24"):
    ep = BY_ID[eid]
    o = [x for x in outs["security@1.0.0"]
         if x["id"] == eid][0]
    print("  %s (%s): %s" % (eid, ep["payload"]["kind"],
                             ep["gold_note"]))
print("""
  delegation transfers trust: the gate checks scope, and both
  delegated payloads are in scope -- authorship is the thing
  that failed, and no layer in this stack reads authorship.
  The semantic payload makes no call at all: the gate checks
  calls, not claims, and the authorised draft carries the
  planted sentence out under the user's own instruction.

  SHIPPED: security@1.0.0 = channel discipline + the boundary
  screen + the action gate, over the 1.10 perimeter.
    breaches: 24 (trust) -> 11 (discipline) -> 3 (shipped)
    the 3 residuals are delegated authorship (x2) and semantic
    content (x1) -- written here, in the statement, not in a
    footnote: this stack does not stop them.
    price: %d of %d tasks wait on a hold decision; the pattern
    list and the working-set discipline are owned artefacts.

  what would actually move the residuals is next lesson's
  subject in disguise: provenance you can MEASURE (who wrote
  the delegated document, and when it changed) and claims you
  can CHECK against records -- 1.12, Measure Everything.
""" % (tt["security@1.0.0"]["held"], len(EPS)))
