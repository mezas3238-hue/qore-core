# VT-08 Index 02/06/10 — Retained Evidence Result

Checkpoint: 2026-09-13

Status: RESEARCH ONLY / CONSUMED EVIDENCE / NOT DEMO ELIGIBLE

## Exact green execution

- Research branch: `agent/vt08-index-02610-retained-evidence-001`.
- Evidence-audit HEAD before this retained-result record: `ced864decfa8ed53196e775cb61c0d6451507b45`.
- Workflow: `VT08 Index 02-06-10 Retained Evidence`.
- Run: `34770525987` — SUCCESS.
- Ruff: PASS.
- Mypy: PASS.
- Focused 02/06/10 evidence tests: PASS.
- Full QORE Gate: PASS.
- Retained-data download: PASS for NAS100, SP500, US30.
- Official aggregate artifact: `10321782011`.
- Artifact name: `qore-vt08-index-02610-retained-evidence-ced864decfa8ed53196e775cb61c0d6451507b45`.
- GitHub artifact digest: `sha256:1a5f3aef8874597295cf7f8df21017c78ea2e04c59afd9e21fe28bcc588d883f`.

The aggregate was downloaded and read after the workflow completed.

## Data lineage

The aggregate consumes retained source-executable V2 run `34661791159` at software SHA `a5b9c6e0d65539c1f755dda8bb3d7ce7b1a839b0`.

This is consumed research evidence, not a fresh holdout.

Canonical/provider mappings:

- NAS100 -> USTEC;
- SP500 -> US500;
- US30 -> US30.

M15 evidence coverage in the retained artifacts runs from approximately 2024-08-13 through 2026-09-11 and contains roughly 49k M15 bars per market.

## Exact 02/06/10 candidate evidence

All anchor hours are `America/New_York` local time.

### NAS100

- Mechanical candidates: 1,631.
- Automatic executable setups: 0.
- Fills: 0.
- Source-judgment-required: 1,631.
- 02:00: 594 candidates; descriptive mean MAE 1.3026144927R; MFE 1.3131324006R; post-signal H4-close +0.0287598142R.
- 06:00: 515 candidates; descriptive mean MAE 2.3363288921R; MFE 2.1242217594R; post-signal H4-close -0.1858930968R.
- 10:00: 522 candidates; descriptive mean MAE 1.0850484186R; MFE 1.0403420741R; post-signal H4-close -0.1068935731R.

### SP500

- Mechanical candidates: 1,639.
- Automatic executable setups: 0.
- Fills: 0.
- Source-judgment-required: 1,639.
- 02:00: 601 candidates; descriptive mean MAE 1.2325034486R; MFE 1.4077915549R; post-signal H4-close +0.0717251343R.
- 06:00: 501 candidates; descriptive mean MAE 2.1376977907R; MFE 1.9633957939R; post-signal H4-close -0.1508538092R.
- 10:00: 537 candidates; descriptive mean MAE 1.0329508355R; MFE 1.0448088260R; post-signal H4-close -0.0168850871R.

### US30

- Mechanical candidates: 1,688.
- Automatic executable setups: 0.
- Fills: 0.
- Source-judgment-required: 1,688.
- 02:00: 652 candidates; descriptive mean MAE 1.2681909676R; MFE 1.3091109219R; post-signal H4-close +0.0629209370R.
- 06:00: 553 candidates; descriptive mean MAE 2.4237191917R; MFE 2.2667430541R; post-signal H4-close -0.1947626277R.
- 10:00: 483 candidates; descriptive mean MAE 0.9713464724R; MFE 1.0140017344R; post-signal H4-close +0.0556154982R.

## Three-market aggregate

- Mechanical candidates: 4,958.
- Automatic executable setups: 0.
- Fills: 0.
- Source-judgment-required candidates: 4,958.

By anchor:

- 02:00: 1,847 candidates; weighted descriptive mean MAE 1.2676492107R; MFE 1.3425141806R; post-signal H4-close +0.0547994512R.
- 06:00: 1,569 candidates; weighted descriptive mean MAE 2.3037047072R; MFE 2.1231003236R; post-signal H4-close -0.1778307434R.
- 10:00: 1,542 candidates; weighted descriptive mean MAE 1.0312906740R; MFE 1.0336470428R; post-signal H4-close -0.0246455585R.

These are descriptive candidate paths only. They are NOT trades and must not be labeled winners, losers, profit factor, expectancy, or strategy P&L.

## Adjudication

The data hypothesis is confirmed: QORE has sufficient retained DEMO market evidence for NAS100, SP500, and US30 to study the 02/06/10 New-York anchors.

The execution hypothesis is NOT yet resolved: the retained source-faithful index contract produces mechanical candidates but does not autonomously resolve them into executable setups. The retained evidence still requires source judgment for point-of-interest selection, qualitative wick classification, source bias context, and unresolved C2 execution context.

Therefore:

- `executable_economic_sample_available = false`;
- `win_loss_pf_claim_authorized = false`;
- `schedule_selection_from_descriptive_paths_authorized = false`;
- `demo_eligible = false`;
- `live_authorized = false`;
- `production_authorized = false`.

The descriptive evidence does show that 02:00 has the strongest pooled H4-close path of the three retained anchors, while 06:00 has the largest MFE and MAE and a negative pooled H4-close path. This is diagnostic only; it does not authorize selecting or discarding an anchor based on P&L.

## Next scientific boundary

Any attempt to generate real win/loss/PF evidence requires a separately versioned and pre-registered executable index candidate. It must resolve source/execution ambiguity before looking at its economic outcomes, must not mutate the certified Forex B01 lineage, and any methodology change requires later fresh unseen validation.
