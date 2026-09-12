# VT-08 R3.8 — Causal Adjudication Freeze for H01-H04

Status: **OPEN CAUSAL INVESTIGATION / RESEARCH ONLY**  
Parent: PR #523 Failure Forensics  
Frozen economic baseline: PR #521, run `34693803930`  
Failure-forensics run: `34696371933`  
Forbidden reuse: `run-34693803930`

## Mission

The failure-forensics campaign established four falsifiable hypotheses. This phase does not optimize VT-08. It opens causal adjudication and separates observed association from source authority and causal mechanism.

No result from run `34693803930` may be used as an independent holdout, to select profitable markets/hours/weekdays, or to resolve a source ambiguity by P&L.

## H01 — Entry and protected-swing quality

Observed signal: 222 of 414 frozen modeled trades terminated at the protected-swing stop.

Causal question: are losses primarily caused by protected-swing provenance/selection, entry-to-PS geometry, unresolved broker stop offset, or genuine structural invalidation after a source-valid B01 setup?

Source constraints:
- protected swing follows important-level interaction plus causal CISD;
- R3.8 requires exactly one valid protected swing or abstention;
- positional historical entry reference is the new H4 open;
- protected-swing broker stop offset is unresolved;
- retrospective nearest/best protected swing is prohibited.

Fresh evidence must log decision-time PS provenance, CISD series/confirmation, PS count, normalized entry-to-PS distance, sweep depth, C2/C3 identity, and path MFE/MAE. Any discriminator must be source-supported and pre-registered before fresh outcome access.

## H02 — Instrument dependency

Observed signal: frozen full-period means were positive for EURUSD/GBPUSD and negative for the other five Forex markets, while only GBPJPY passed OOS and no market passed Stress.

Causal question: is the dispersion a stable methodology-by-instrument interaction, a regime/microstructure interaction, sample variation, or an evidence-construction artifact?

All seven source-authorized Forex markets remain in the next fresh campaign. EURUSD/GBPUSD may not be whitelisted and the five negative markets may not be blacklisted from the consumed ranking.

## H03 — Source-anchor/regime interaction

Observed signal: 05:00 New York was modestly positive in the consumed campaign while 01:00 and 09:00 were negative.

Source constraints:
- source-complete Forex timing: 01/05/09/13 New York;
- Human Owner operational subset: 01/05/09 New York;
- 05:00 has no source authority as a privileged winner;
- source-complete and Owner-subset statistics must remain distinct.

Fresh evidence retains all three Owner anchors and separately diagnoses 13:00 under a source-complete profile. No 05:00-only Trader may be created from the frozen result.

## H04 — Operational containment effect

Observed signal: 107 trades ended by H4 containment and that subset was positive in the frozen campaign.

R3.8 explicitly labels `close-modeled-position-at-next-h4-boundary` as a QORE research containment. Source-explicit behavior for a filled position across an H4 boundary remains unresolved. The conservative 2R target and no-stop-offset model are also containments rather than universal TTrades rules.

Fresh causal work must first adjudicate any lifecycle alternative from source evidence, then pre-register it. Counterfactual post-H4 path logging may be collected diagnostically, but it may not change the executed replay until source and preregistration gates are satisfied.

## Global decision gate

A causal hypothesis may advance only if:
1. source adjudication precedes methodology mutation;
2. the intervention/discriminator is pre-registered;
3. evaluation uses previously unseen dates;
4. all seven Forex markets and 01/05/09 Owner anchors remain observable unless source evidence independently changes authority;
5. OOS improves in a mechanism-consistent way and Stress survival is not degraded;
6. the result survives falsification without retrospective slicing.

Until then all H01-H04 remain `OPEN_CAUSAL_ADJUDICATION` and `DEMO_ELIGIBLE = false`.
