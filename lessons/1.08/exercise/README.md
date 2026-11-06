# Exercise 1.08 — File only what validates

The starter's `extract.py` in this folder is the extractor as
found wherever a model's output is consumed without a
contract: `json.loads`, then file whatever came out. Run the
harness against it before you change anything and read its
report properly — it files six records that do not satisfy
the schema into the system of record, loses seven more to
parse failures it cannot name, and its three honestly filed
records still include a wrong label. That is not a broken
starter. It is the industry default, measured.

## The task

Replace `extract(reply_text)` in `extract.py` until the
harness reports **all three bars met**. You are given sixteen
raw replies as data (`records.json`, golds included) — the
replies a model already sent. There is no model to re-ask:
the lesson's loop is not available here, and that is
deliberate. What you build is the deterministic half of the
shipped pipeline: repair what is mechanically repairable,
validate everything, and reject — inside the yield budget —
what the contract forbids you to guess.

The three bars, stated in the lesson before any code:

- **validity** — every record you emit validates against
  record@1.0.0 (`../solution/structured.py` holds the schema
  and the validator; they are the shared contract, not yours
  to edit). One invalid emission fails the run. Downstream
  code files what you emit.
- **yield** — at least 13 of the 16 replies produce a record.
  Rejection is legitimate and priced: exactly three of these
  replies cannot be filed honestly.
- **accuracy** — field accuracy at or above 0.95 over the
  records you file: every field exact, except the summary,
  which is graded on carrying the case's printed key phrase.

## The traps, named in advance

**Emit everything** and validity fails: hope is not a
strategy, it is the absence of one. **Reject everything**
and validity is perfect while yield fails — a contract that
files nothing is a very safe outage. **Emit a constant
record** — always valid, and the accuracy bar exists
precisely to bury it: it scores about 0.2. And the subtle
one: **the synonym map**. One reply files its priority as
"medium". You could map it to "normal" — it is probably
right! It is also a judgement, made by your code, silently,
forever, on every future synonym the world invents. The
contract's answer to an unmechanical defect is rejection,
and the yield bar is set so that honesty is affordable:
three rejections are budgeted. Spend them exactly there.

One warning about repairs, from the lesson: a repair you
cannot log is a guess you cannot audit. The lesson's repair
layer names every move it makes. Yours should be able to
say, for every record it files, what was wrong with the
reply and what it did about it — or it should not file the
record.

## The rules of the road

- Standard library only. The schema and validator come from
  `../solution/` (already importable from the harness);
  records.json is the shared set.
- The interface is the contract: `extract(reply_text)`
  returns a record dict to file, or `None` to reject.
- A record your extractor cannot defend — which repairs
  fired, or why none were needed — is a record it should
  not file.

## How you are graded

    python3 records_harness.py --extractor extract.py   # grade yours
    python3 records_harness.py                          # grade the worked solution

Run it against the starter first to see the honest baseline:
three bars missed, each failure a way the wild gets into a
system of record. The worked answer lives in
`solution/extract.py` in this folder: it delegates to the
lesson's shipped repair layer and validator, files 13,
rejects the budgeted three by name, and scores 0.985. Try
the exercise before you read it; then be able to explain, in
one sentence each, why the missing key is not a null, why
"medium" is not "normal", and why a repair log is part of
the contract.
