# VT-31 R2.5 — Multi-Index Transfer Research 001

Checkpoint: 2026-09-14

Status: **RESEARCH ONLY — NO DEMO/LIVE/REAL-CAPITAL AUTHORITY**

## Source and correction

The primary authority remains the Human Owner file `1000856441.mp4`, TTrades
`youtube:o0v4KQxZbpU`, SHA-256
`bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf`.

Direct audio/visual reinspection confirms:

- NQ/NAS100 is the demonstrated source market;
- the 09:00-10:00 New-York range and 10:00-11:00 entry window are explicit;
- strict high raid seeks SHORT and strict low raid seeks LONG;
- post-raid reversal structure is required;
- Breaker, Order Block and FVG entries are all demonstrated;
- unfilled entries expire at 11:00 while filled positions may remain open;
- reaching 3R arms breakeven;
- the opposite 09:00 range boundary is the target.

R2.4 incorrectly elevated the FVG-CE/midnight-open confluence at `02:30-02:55`
from `SINGLE_EXAMPLE` to a universal equality and restricted the implementation
to SHORT. Those restrictions produced zero setups and are not retained as
universal TTrades rules.

## Owner-authorized transfer boundary

The Human Owner authorizes research on `NAS100`, `SP500` and `US30`. This does
not rewrite TTrades source scope. Reports preserve both facts:

- `source_market=NAS100`;
- `owner_authorized_transfer_markets=[NAS100, SP500, US30]`.

All three receive exactly the same configuration. No market-specific threshold,
target, session or direction rule is permitted.

## Predeclared ambiguity grid

The source supports three entry families but does not define a universal exact
price inside every zone. Before acquiring SP500 or US30 M1 evidence, R2.5 freezes
nine research translations:

| Family | Zone points |
|---|---|
| Breaker | near-stop boundary, midpoint, near-target boundary |
| Order Block | near-stop boundary, midpoint, near-target boundary |
| Fair Value Gap | near-stop boundary, midpoint/CE, near-target boundary |

These are hypothesis tests, not nine approved strategies. `hypothesis_count=9`
is retained in every artifact. Near-stop/near-target and block midpoints are
QORE operationalizations with `source_rule=false`.

## Identical execution contract

- M1 closed evidence only;
- `America/New_York`, DST-aware;
- frozen 09:00-10:00 range;
- `[10:00,11:00)` setup/fill window;
- strict first-side raid; both sides swept abstains;
- structural-close confirmation;
- selected entry family and zone point;
- stop at raid extreme with no invented buffer;
- target opposite frozen range boundary;
- 3R touch arms breakeven;
- pending order expires at 11:00;
- filled position has no invented 11:00 exit;
- provider gap censors;
- unknowable same-bar path censors.

## Candidate-grade research gates

A variant is only a research survivor if all gates pass concurrently:

- aggregate terminal sample at least 150;
- at least 30 terminal observations in each market;
- aggregate mean remains positive after `0.05R/trade`;
- aggregate stressed PF at least 1.10;
- aggregate stressed max drawdown at most 20R;
- every market has positive stressed mean;
- LONG and SHORT have positive stressed mean;
- at least three of four chronological quartiles are positive;
- at least two thirds of eligible market-year blocks are positive.

Multiple survivors do not authorize choosing the best P&L. They produce an
ambiguous result and require further falsification. Exactly one survivor may be
proposed for a separate frozen-candidate commit and genuinely fresh validation.

## Starting NAS100 consumed evidence

The official R2.4 run `34698291771`, HEAD
`1a102abd2518cee3d0fe73f9e5fcd45cd5d23c07`, artifact `10300155064`, found zero
setups because of the invalid universal exact-midnight equality. Replaying the
predeclared ambiguity grid on that now-consumed NAS100 evidence is research,
never fresh validation.

No candidate is frozen by this document.

## Acquisition reproducibility correction

The first R2.5 run at `06b93fb36856c247da77e7221301082a313866d4`
exposed a collector defect before adjudication could be accepted.  Its
fourteen-calendar-day M1 requests could exceed cTrader's 5,000-bar page, while
the provider did not reliably report more pages.  Repeated NAS100 acquisitions
therefore agreed exactly on shared timestamps but omitted different time
blocks.  All economic output from that run is invalid research evidence.

VT-31 now requests no more than three calendar days at a time (at most 4,321
inclusive M1 openings), serializes the three market acquisitions, and retains
the existing contradiction and duplicate checks.  Only artifacts produced
after this correction may be adjudicated.

`VT31_CANDIDATE_FROZEN=false`

`VT31_DEMO_ELIGIBLE=false`

`LIVE_AUTHORIZED=false`

`REAL_CAPITAL_AUTHORIZED=false`

`PRODUCTION_AUTHORIZED=false`
