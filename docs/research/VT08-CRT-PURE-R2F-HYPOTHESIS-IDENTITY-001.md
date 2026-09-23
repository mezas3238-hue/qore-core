# VT08 CRT PURE — R2-F MODEL #1 HYPOTHESIS IDENTITY LEDGER 001

**Identity:** `VT08_CRT_PURE_R2F_MODEL1_HYPOTHESIS_IDENTITY_LEDGER_001`  
**Workflow run:** `35809223057`  
**Evidence HEAD:** `99f8d4a4d7dbf517c88bf470002e90ca8ab124f8`  
**Status:** CHARACTERIZATION COMPLETE / COMPETITION POLICY OPEN  
**Methodology mutated:** FALSE  
**Trades created:** 0  
**PnL evaluated:** FALSE

## 1. Question

R2-E proved that the engineering control:

`single_source_event_per_parent = true`

suppresses material later Model #1 source structure.

R2-F does not trade those sources. It gives every causal direction-aligned Model #1
source event:

- a deterministic `source_event_id`;
- a deterministic `hypothesis_id`;
- a parent-local `event_generation`;
- the exact reference evidence IDs that created the source;
- the confirmation state known by C3 close.

This separates:

`new independent source event`

from:

`fallback / revival of the same hypothesis`.

## 2. Authority boundary

The cognitive architecture already requires a new source event and new hypothesis identity
for genuine rearm after invalidation.

R2-F uses that identity discipline for characterization only.

It does **not** source-close:

- whether several Model #1 hypotheses may be traded inside one parent C3;
- which hypothesis wins if several coexist;
- whether confirmation of one kills the others;
- whether one entry per parent is mandatory;
- whether a later independent source is rearm, competition or a separate opportunity.

Those remain open.

RomeoTPT primary material supports Model #1 as a major source-authorized entry model, but
no reviewed primary rule currently authorizes QORE to invent a same-parent competition
algorithm.

## 3. Causal safeguards

- Existing R2-C close-unmitigated source builder reused.
- Every source event gets a stable hash identity from market, parent C3, source time and
  reference evidence IDs.
- Duplicate source/hypothesis IDs fail closed.
- Body confirmation is tracked only when its candle closes.
- A next contiguous M15 slot is recorded as availability only; it grants no entry.
- Multiple hypotheses do not imply multiple entries.
- No target, stop or expiry evaluation.
- No PnL.
- No capital authority.

## 4. Validation

Run `35809223057` completed SUCCESS.

- Quality: SUCCESS
- Ruff: SUCCESS
- Mypy: SUCCESS
- Pytest: SUCCESS
- AUDUSD ledger: SUCCESS
- USDJPY ledger: SUCCESS
- BTCUSD ledger: SUCCESS

Cognitive Gate on evidence HEAD `99f8d4a4d7dbf517c88bf470002e90ca8ab124f8`:
`35809223019 — SUCCESS`.

## 5. AUDUSD

Parent CRT: **287**

- zero aligned source: 49
- exactly one source: 82
- multiple sources: 156
- total source events: 563
- later source events: 325
- events still awaiting at C3 close: 327
- events with body confirmation + contiguous next slot: 217
- parents with any confirmed entry slot: 156
- parents with a later confirmed entry slot: 74
- parents with concurrent awaiting hypotheses: 135
- maximum observed awaiting concurrency: 8

Temporal split:

- Year 1: 153 parents / 307 source events / 74 concurrent parents
- Year 2: 134 parents / 256 source events / 61 concurrent parents

## 6. USDJPY

Parent CRT: **267**

- zero aligned source: 44
- exactly one source: 79
- multiple sources: 144
- total source events: 528
- later source events: 305
- events still awaiting at C3 close: 320
- events with body confirmation + contiguous next slot: 191
- parents with any confirmed entry slot: 139
- parents with a later confirmed entry slot: 69
- parents with concurrent awaiting hypotheses: 128
- maximum observed awaiting concurrency: 7

Temporal split:

- Year 1: 136 parents / 286 source events / 70 concurrent parents
- Year 2: 131 parents / 242 source events / 58 concurrent parents

## 7. BTCUSD

Parent CRT: **459**

- zero aligned source: 60
- exactly one source: 109
- multiple sources: 290
- total source events: 993
- later source events: 594
- events still awaiting at C3 close: 505
- events with body confirmation + contiguous next slot: 460
- parents with any confirmed entry slot: 300
- parents with a later confirmed entry slot: 180
- parents with concurrent awaiting hypotheses: 238
- maximum observed awaiting concurrency: 8

Temporal split:

- Year 1: 234 parents / 493 source events / 117 concurrent parents
- Year 2: 225 parents / 500 source events / 121 concurrent parents

## 8. Combined 3-market characterization

Parent CRT: **1,013**

Source events: **2,084**

Later source events: **1,224**

Parents:

- zero source: **153**
- exactly one source: **270**
- multiple sources: **590 / 1,013 = 58.2%**
- with concurrent awaiting hypotheses: **501 / 1,013 = 49.5%**
- with any confirmed entry slot: **595 / 1,013 = 58.7%**
- with a later confirmed entry slot: **323 / 1,013 = 31.9%**

Event states:

- still awaiting at C3 close: **1,152**
- body-confirmed with contiguous next slot: **868**

Observed maximum simultaneous awaiting hypotheses:

- AUDUSD: 8
- USDJPY: 7
- BTCUSD: 8

## 9. Adjudication

The data falsifies any assumption that one Model #1 source event naturally represents the
entire hypothesis space of a parent C3.

Nearly half of all parent CRTs contain overlapping unconfirmed hypotheses under the existing
causal source construction.

That is a cognition/lifecycle problem before it is an economic problem.

Therefore the next experiment must **not** simply execute all 868 confirmed slots or all
323 parents with a later confirmed source.

## 10. Required next closure

Before economic replay, freeze an explicit same-parent competition contract that answers:

1. Can several source hypotheses coexist before any confirms?
2. What observation invalidates one source hypothesis independently of the parent CRT?
3. Does confirmation of one source kill, suspend or leave competitors alive?
4. Is a later source after an earlier WAIT a new hypothesis or a rearm event?
5. Is there source authority for one-entry-per-parent, or is that only an engineering
   exposure-control policy?
6. How are Journey / Key Level / destination context attached to each hypothesis rather
   than only to the parent CRT?

Until these are closed:

`competition_policy_frozen = false`

and no multi-hypothesis economic candidate may be promoted.

## 11. Governance

- PR DRAFT / UNMERGED.
- No merge.
- No VPS.
- No runtime registration.
- No DEMO activation.
- No LIVE activation.
- No production authority.
- No real-capital authority.
