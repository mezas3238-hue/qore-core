# VT-08 Index V4 Root-Cause Forensics

## Decision

`V4_CANDIDATE_NOT_JUSTIFIED`

`VT08_INDEX_V4 = REJECTED`

Phase 2 finds a material context defect in V3, but does not find a candidate-grade rule that
survives the complete stability and multiplicity contract. No fresh evidence was opened. No V4
identity or fingerprint was created. Index remains in research and is not DEMO eligible.

```text
V4_RESEARCH_OPEN=true
V4_CANDIDATE_FROZEN=false
VT08_INDEX_DEMO_APPROVED=false
ACCOUNT_PURCHASE_AUTHORIZED=false
ORDER_SUBMISSION_AUTHORIZED=false
REAL_CAPITAL_AUTHORIZED=false
LIVE_AUTHORIZED=false
PRODUCTION_AUTHORIZED=false
```

## Evidence boundary

The study uses only the three consumed windows and their already-sealed artifacts:

| Window | Role | V3 replay trades | Mean R | PF | Max DD |
|---|---|---:|---:|---:|---:|
| 2022-09-15 to 2023-09-15 | consumed V3 fresh | 51 | -0.177497 | 0.5962 | 11.4929R |
| 2023-09-15 to 2024-08-13 | consumed V2 fresh, V3 mechanics | 42 | +0.271466 | 1.9095 | 5.1303R |
| 2024-08-13 to 2026-09-12 | consumed development | 90 | +0.228470 | 1.7700 | 6.1275R |

The official V2 and V3 causal-equivalence artifacts are both PASS. The Phase-2 ledger contains 183
trades. Every predictive feature is available at or before `signal_at`; future path fields are named
`outcome_*` and are labels or diagnostics only. The run never requests an older tranche or forward
DEMO data. [1][2][3]

## Feature census

The ledger reconstructs daily sequence, previous/current source-day alignment, sweep/reclaim family,
C2/C3 closure, protected-swing count and selected rank, opposing-series length, CISD confirmation
latency, CISD-to-extreme distance, normalized sweep/reclaim depth, closure expansion, protected risk,
causal H4 and daily range state, and contemporaneous cross-index state. It also records MAE/MFE and
counterfactual target outcomes strictly as post-entry diagnostics.

Range descriptors use fixed, declared descriptive bands (`<0.8` compressed, `>1.2` expanded). They
are not represented as TTrades rules and are not promoted. CISD level and protected-swing extreme
remain separate throughout reconstruction.

## Root cause

V3 combines two economically different previous-source-day contexts:

| Previous source-day body vs trade side | 2022-23 | 2023-24 | 2024-26 |
|---|---:|---:|---:|
| Opposed | 22 trades, +0.1263R/trade | 25, +0.2464R | 36, +0.2714R |
| Aligned | 29 trades, -0.4079R/trade | 17, +0.3083R | 54, +0.1998R |

The V3 sign flip is therefore driven principally by the aligned-context family changing from severe
loss in 2022-23 to positive expectation later. The opposed family stays positive in all three broad
windows after 0.05R/trade friction, but its frequency does not increase monotonically (43.1%, 59.5%,
40.0%). Frequency shift alone is not the explanation. The unresolved defect is that the daily-bias
resolver admits a non-stationary aligned family without a causal state variable that distinguishes
its bad and good regimes.

This is a context-classification/admission failure. It is not explained by removing a market, side,
or anchor, and is not repaired by a target multiple.

## Falsification register

Eighteen predeclared, interpretable screens were evaluated. Holm-Bonferroni controls family-wise
error across the screen family. Candidate admission additionally requires at least 60 trades,
positive 0.05R-stressed expectation in all three windows, internal stressed robustness across
markets/sides/anchors inside every window, and broad aggregate participation.

| Hypothesis | N | Aggregate mean | 0.05R mean | Three-window aggregate stress | Stratified stability | Result |
|---|---:|---:|---:|---|---|---|
| Previous body opposed | 83 | +0.2254R | +0.1754R | PASS | FAIL | research lead only |
| CISD confirmation in first half | 106 | +0.1223R | +0.0723R | PASS | FAIL | falsified as candidate |
| Opposed + early CISD | 48 | +0.2038R | +0.1538R | FAIL | FAIL | falsified |
| Opposed + C2 | 13 | +0.8444R | +0.7944R | PASS | FAIL/sample | insufficient sample |
| Opposed + C3 | 70 | +0.1104R | +0.0604R | FAIL | FAIL | falsified |
| Opposed + reversal bias | 50 | +0.2459R | +0.1959R | FAIL | FAIL | falsified |
| Opposed + breakout bias | 33 | +0.1943R | +0.1443R | FAIL | FAIL | falsified |
| Opposed + cross-index not-against | 79 | +0.2228R | +0.1728R | PASS | FAIL | falsified as candidate |
| Protected swing count = 2 | 58 | +0.1596R | +0.1096R | FAIL | FAIL | falsified |
| Single protected swing | 93 | +0.1509R | +0.1009R | FAIL | FAIL | falsified |
| Short opposing series | 170 | +0.1042R | +0.0542R | FAIL | FAIL | falsified |
| Current body aligned | 135 | +0.0934R | +0.0434R | FAIL | FAIL | falsified |
| H4 not expanded | 5 | +0.6192R | +0.5692R | FAIL/sample | FAIL | insufficient sample |
| Daily not expanded | 117 | +0.1216R | +0.0716R | FAIL | FAIL | falsified |
| Cross-index unanimous with side | 126 | +0.0917R | +0.0417R | FAIL | FAIL | falsified |
| Cross-index mixed | 53 | +0.1933R | +0.1433R | FAIL | FAIL | falsified |
| Daily sweep/reclaim | 80 | +0.1985R | +0.1485R | FAIL | FAIL | falsified |
| Opposed + early CISD + C2 | 3 | +0.6269R | +0.5769R | FAIL/sample | FAIL | insufficient sample |

The strongest lead, previous-body-opposed, fails internal stability in 2022-23 and 2023-24: only one
side remains positive after friction in each window; only one anchor is positive in 2022-23. It also
fails family-wise significance (`Holm-adjusted p = 0.429`). Six-month blocks include negative
2023-H2 and 2026-H2 slices. It cannot be frozen honestly.

## Payoff falsification

Changing the target does not explain or repair the regime flip:

| Target | All-window mean | 2022-23 | 2023-24 | 2024-26 |
|---|---:|---:|---:|---:|
| 1.5R | +0.1119R | -0.1820R | +0.1598R | +0.2560R |
| 2.0R | +0.1238R | -0.1873R | +0.2119R | +0.2590R |
| 2.5R | +0.1252R | -0.1775R | +0.2715R | +0.2285R |
| 3.0R | +0.1211R | -0.1838R | +0.2816R | +0.2190R |

Every tested payoff remains negative in 2022-23 and positive later. Selecting 3R for its better
2023-24 result would be post-hoc target mining.

## Temporal and structural interpretation

Early CISD is directionally promising at broad-window level but fails market/side/anchor stability.
Protected-swing multiplicity fails replication in 2024-26. Cross-index direction does not isolate the
bad regime. C2 within the opposed family is unusually strong but has only 13 observations, including
only two in 2022-23; it cannot carry a frozen candidate.

The evidence supports a narrow conclusion: V3 is incomplete because it lacks a stable causal
context resolver for previous-source-day alignment. It does not yet support the stronger claim that
“opposed” is the missing rule. Additional evidence must be accumulated forward after a separately
pre-registered hypothesis, or the source/context reconstruction must identify another pre-entry
state with a non-post-hoc rationale.

## Candidate and validation adjudication

No candidate is frozen, so there is no candidate ID, rule fingerprint, fresh tranche, candidate
stress gate, Monte Carlo, or candidate causal-equivalence run. Reporting fabricated zero-trade
metrics for those stages would be misleading; their state is `NOT_RUN_NO_CANDIDATE`.

The only defensible terminal outcome for this phase is rejection. Index promotion remains blocked
while VT-08 Forex #532 remains untouched and retains its independent status. [4]

## Sources

1. QORE Core, [Issue #547 — VT-08 Index V4 Regime/Context Failure Forensics](https://github.com/mezas3238-hue/qore-core/issues/547), accessed 2026-09-14.
2. QORE Core, [PR #548 — VT-08 Index V4 regime/context forensics](https://github.com/mezas3238-hue/qore-core/pull/548), accessed 2026-09-14.
3. QORE Core, [Phase-1 workflow run 34801520494](https://github.com/mezas3238-hue/qore-core/actions/runs/34801520494), artifact 10330789887, digest `sha256:a9a68c7d5a2ed89c41841e88fae620f0ac39b1fb770a23c924cfa9357355d35c`.
4. QORE Core, [PR #532 — VT-08 Forex final independent validation](https://github.com/mezas3238-hue/qore-core/pull/532), accessed 2026-09-14.
