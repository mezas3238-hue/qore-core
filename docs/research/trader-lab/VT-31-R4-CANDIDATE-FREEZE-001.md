# VT-31 R4 Candidate Freeze 001

Status at this document: candidate frozen for one-shot fresh falsification; not DEMO approved.

## Identity

- Candidate: `VT31_R4_TTRADES_NY_REVERSAL_001`
- Research parent: PR #550, branch `agent/vt31-r2-5-multi-index-validation-001`
- Candidate branch: `agent/vt31-r4-ny-reversal-candidate-001`
- Research survivor run: `34893281766`
- Research artifact: `10367912073`
- Research artifact digest: `sha256:cd1688e0818843a338b51244b79fbf7cea4b55a9c78afb7af20dd37991188be7`
- Frozen contract fingerprint: `5bccaf9677fa9a07f3e5827b0d8f186f02bccc11783e67d7473a6cee1de8a41a`

The exact software SHA is the SHA recorded by the final successful candidate-freeze
artifact. Any later code or contract change invalidates that freeze and requires a new
candidate identity before fresh evidence may be opened.

## Source chain and scope

NAS100 remains the TTrades source market. SP500 and US30 are Human
Owner-authorized transfer markets and receive the identical configuration. The source
chain is New York reversal daily profile, CISD/protected swings, rejection quality,
relative-strength event selection, and lower-timeframe protected-swing trailing.
No outcome-derived market, side, day, or time filter is used.

## Frozen decision contract

- Source day: 18:00–17:00 America/New_York.
- POI: previous completed source-day high or low.
- London failure: 02:00–05:00 does not reach the eligible POI.
- NY event window: 08:30–10:30.
- Event: first eligible prior-source-day extreme sweep.
- Confirmation: M5 CISD through the first candle of the opposing series.
- Quality: confirmation body is side-aligned and at least as large as its opposing wick.
- Cross-index collision: maximum directional body fraction; exact ties abstain.
- Entry: M5 confirmation close.
- Initial invalidation: M5 protected opposing-series extreme.
- Management: trail only after a new M1 protected swing is confirmed by a sweep and
  close through its opposing series; the initial-risk denominator never changes.
- Target: opposite London session extreme.
- Lifecycle: 16:00 America/New_York.
- Same-bar ambiguity: censor.
- Data gap: censor.
- Cost gate: 0.05R/trade. Additional research stresses: 0.025R, 0.075R and 0.10R.

The machine-readable source of truth is
`vt31_r4_ny_reversal_candidate.contract_payload()`.

## Consumed-evidence falsification

The research survivor had 166 terminal trades. Candidate implementation added the
predeclared conservative gap-censor policy, censoring ten trades and leaving 156.
This containment was fixed before fresh acquisition and was not selected from outcome.

Candidate replay on consumed evidence:

- sample 156; wins 72; losses 84;
- total +45.7335398997R; mean +0.2931637173R;
- PF 1.6981008293; max DD 13.7445959343R;
- after 0.05R/trade: +37.9335398997R, mean +0.2431637173R,
  PF 1.5437522142, max DD 14.9945959343R;
- all frozen economic gates pass;
- full versus decision-truncated causal equivalence must pass in the freeze artifact.

## Fresh boundary and gates

The one-shot historical request is exactly 760 calendar days ending exclusively at
`2024-08-15T00:00:00Z`. These bars were not opened during VT-31 candidate research.
If the provider cannot supply at least 730 actual days for all three markets, the
candidate is not approved from historical fresh evidence and must wait for forward
DEMO evidence. The boundary must not be changed after seeing results.

Fresh gates remain:

- aggregate sample at least 150;
- each market sample at least 30;
- stressed mean positive and PF at least 1.10;
- stressed max DD at most 20R;
- every market and both sides positive after stress;
- at least 3/4 chronological quartiles positive;
- at least 2/3 eligible temporal blocks positive;
- deterministic 10,000-path moving-block bootstrap;
- positive-terminal probability at least 0.70;
- p95 max DD at most 20R;
- causal equivalence PASS.

There is no retuning after acquisition. A failed gate adjudicates
`VT31_R4_REJECTED`.

## Authority

`VT31_R4_CANDIDATE_FROZEN = TRUE` only for the exact successful freeze SHA.

`VT31_R4_DEMO_ELIGIBLE = FALSE` until one-shot fresh PASS.

`LIVE_AUTHORIZED = FALSE`

`REAL_CAPITAL_AUTHORIZED = FALSE`

`PRODUCTION_AUTHORIZED = FALSE`
