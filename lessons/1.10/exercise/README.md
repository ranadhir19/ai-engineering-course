# Exercise 1.10 — Gate the Perimeter

Sixteen crossings arrive as data in `crossings.json`:
five requests in, four tool results back, seven records
read back from rest. There is no sender to correct them
and no model to hand errors back to — the feedback loops
of 1.08 and 1.09 are gone by design. What you build is
the gate standing alone: the code that answers, for
every crossing, *what are you, and may you pass?*

## Your task

Replace the found gate in `admit.py` — a pass-through
that decodes what parses, forwards everything, and logs
nothing — with a gate that returns, for the crossings
it is given:

- `admitted`: the forms that may enter, keyed by
  crossing id (for records, the record itself);
- `log`: an entry for **every** crossing — admitted or
  not — with a `disposition` (one of `admit`, `repair`,
  `quarantine`, `reject`) and a non-empty `reason`, the
  located, named kind the course has used since 1.08.

Admit what satisfies its contract as it stands. Repair
what the closed, mechanical rule set settles —
whitespace and control characters, undeclared keys in a
closed contract, and the **versioned migrations**
(a crossing stamped with an older contract version is
translated by that version's printed table, never by
guessing) — and admit the repaired form. Quarantine
what is interpretable but not admissible: over a cap, a
value no version ever allowed, a result under the wrong
contract. Reject what cannot be interpreted at all.
The contracts and the shipped machinery live in
`../solution/boundary.py`; the harness re-validates
your admitted forms against them.

## The bars

Graded by `boundary_harness.py`:

1. **Safety (absolute):** zero invalid admissions —
   every admitted form satisfies its contract on
   re-validation. Downstream reads what you admit,
   and it trusts it.
2. **Yield:** at least 7 of the 8 legitimate crossings
   (the ones whose gold disposition is admit or
   repair) admitted in valid form. The other eight
   cannot be admitted honestly; the budget prices
   that, it does not forgive guessing your way past it.
3. **Accounting:** every crossing carries a named
   disposition with a reason, and at least 3 crossings
   are held in quarantine. Nothing vanishes silently
   in either direction — neither admitted without a
   word nor dropped without one.

## The traps, named in advance

- **Coerce your way to yield.** Map `urgent` to `high`,
  truncate the over-cap summary, cast the string count.
  Yield climbs — and you have become the crossings'
  co-author, inventing content the sender never sent.
  The harness cannot catch all of it; that is why it is
  named here instead.
- **Refuse everything.** Safety is perfect, accounting
  is easy, and the system admits nothing — a very safe
  outage, buried by the yield bar.
- **Admit everything in repaired form.** Calling a
  quarantine a repair does not settle it; the held
  count is a bar, not a suggestion.
- **Drop silently.** A crossing with no log entry is
  the pass-through's original sin, and the accounting
  bar counts it.

One crossing (x-15) is formally perfect and wrong — a
record whose label is the 1.09 judgement error, filed
faithfully. Every honest gate admits it. The exercise
does not punish that; it asks that your reason says
what is true about it: the form is valid, and form is
all a gate can certify.

## Pass condition

From this folder:

    python3 boundary_harness.py --gate admit.py

reports **all 3 bars met** and exits 0. The worked
solution is in `solution/` (0 invalid, 8 of 8
legitimate admitted, 4 held, every disposition as
gold); the found gate misses all three (12 invalid
admitted, 4 of 8 in valid form, nothing accounted for).
