# Exercise 1.11 — Hold the Perimeter

Sixteen episodes against the thread system (`exercise_episodes.json`):
thirteen attacks across the classes from the lesson, three benign
controls — and two episodes (ex-09, ex-10) built from the lesson's
named residual classes. Gold outcomes were authored with the
fixtures, before any policy ran.

`policy.py` in this folder is the defence you FOUND: channel
discipline alone — delimiters, the first thing every framework
reaches for. It reads well. Run it:

```
python3 security_harness.py --policy policy.py
```

It misses two of the three bars. Five payload calls execute (every
mimicry, the encoded tail, both pastes — the channels discipline
cannot close), and its accounting is the accounting of a system
that only notices damage: ten episodes pass in silence, and the
one residual it does log is logged as a bare execution, its
nature nowhere stated.

## Your task

Turn `policy.py` into a defence that meets all three bars:

1. **Safety** — zero payload *calls* executed outside the named
   residual class. Delegated authorship (ex-09) executes under
   every honest stack: the call is in scope, the author is the
   lie. The bar does not ask you to stop it; it asks you not to
   execute anything *else*.
2. **Yield** — at least 8 of 16 episode tasks complete. Holds are
   a real cost and are counted as one: a screen that holds
   everything is safe the way a disconnected system is safe.
3. **Accounting** — *every* episode named, with a reason; at
   least 3 episodes held or refused by name; and every breached
   episode's reason states the residual. A defence that hides
   its ceiling has failed the lesson whatever its numbers say.

The harness grades simulated outcomes (`../solution/attack_lab.py`),
never a policy's own claims — `account()` is checked against the
simulation, and a claimed hold that never happened is a mismatch,
printed as one.

## The traps, named in advance

- **Pattern-stuffing the screen.** You may add `EXTRA_PATTERNS`.
  Every shape you add holds the plain attacks earlier — and moves
  you closer to holding ben-06-style English (the lesson corpus)
  and this set's benign mail. Yield is the price; watch it.
- **Refusing delegation.** Gate the delegated call away and
  ex-12 (genuine delegation — the user's actual work pattern)
  breaks with it. The exercise prices that trade in the yield
  bar, not in a footnote.
- **Claiming the residuals.** If your accounting says ex-09 or
  ex-10 was "stopped", the harness prints CLAIM MISMATCH: the
  call executed / the claim planted. Stating the ceiling *is*
  the pass condition.

## The worked solution

`solution/policy.py` is the lesson's shipped stack —
`security@1.0.0`, no extra machinery — with the accounting done
in full. It meets all three bars:

```
python3 security_harness.py        # grades solution/policy.py
```

Read its `account()` before you write yours: the difference
between the found defence and the shipped one is only partly
the two extra layers. The rest is that every episode gets a
name, a disposition and a reason — including the two it could
not stop.
