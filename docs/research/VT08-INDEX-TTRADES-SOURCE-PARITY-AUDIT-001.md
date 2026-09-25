# VT-08 INDEX — TTRADES SOURCE PARITY AUDIT 001

Checkpoint: 2026-09-16
Status: SOURCE-TO-CODE AUDIT / CONSUMED-EVIDENCE ONLY
Fresh holdout 2020–2022: SEALED

## Purpose

This audit compares the current VT-08 Index research stack against the Human Owner-authorized TTrades primary lesson `Trading The 4 Hour Power Of Three - OHLC / OLHC` (`youtube:FAKWJ-1NlLE`, SHA-256 `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`) and same-author prerequisite/clarification material. The goal is source fidelity, not retrospective P&L optimization.

Classification:
- `MATCH`: implementation materially follows the author.
- `PARTIAL`: author concept exists but software encodes only a subset/proxy.
- `QORE_ADDITION`: mandatory software rule not established as a universal TTrades rule.
- `SOURCE_CONFLICT`: software behavior materially contradicts or replaces the author framework.
- `MISSING`: author-required/contextual component is absent from the current candidate.

## Primary conclusion

The current D1 stack is **not a source-faithful reproduction of TTrades H4 PO3 / Fractal Model**. It preserves the broad skeleton (daily context -> H4 C2/C3 -> M15 CISD/protected swing -> expansion), but several source-ambiguous judgments were converted into hard QORE admission rules. Those hard gates are a plausible explanation for both sparse frequency and regime instability.

The most important failure is architectural: TTrades treats context, POI, wick completion, CISD/continuation and relative strength as a causal sequence. QORE replaced several of those contextual stages with numeric thresholds, daily uniqueness and a simultaneous-signal-count proxy.

## Rule-by-rule parity matrix

| Component | TTrades source | Current VT-08 Index | Classification | Consequence |
| --- | --- | --- | --- | --- |
| H4 PO3 | Accumulation -> manipulation -> distribution/expansion | H4 sequence retained | MATCH | Keep |
| Daily directional context | Previous-day close/continuation and sweep/reversal logic; higher-timeframe alignment | Mechanical previous-day continuation/reversal resolver | MATCH/PARTIAL | Direction formula is useful, but primary H4 lesson does not make it the only context source |
| H4/M15 pairing | H4 structure with M15 confirmation demonstrated | H4 derived from M15; M15 confirmation | MATCH | Keep |
| Futures H4 timing | Full repeating family includes 18/22/02/06/10/14 NY; important active levels include 02/06/10/14 | Owner subset scans only 02/06/10 | PARTIAL | Source-valid windows are omitted; 14:00 is an obvious missing active anchor and 18/22 are reconstruction/context windows in the full family |
| C2 definition | C2 is reversal closure: sweep previous candle extreme and close back inside, at a valid HTF POI | Sweep/inside logic implemented, plus rejection if opposite extreme also swept | PARTIAL/QORE_ADDITION | Extra `not other_sweep` restriction may discard source-valid C2s; POI context is incomplete |
| C2 wick logic | Shallow opposing wick/run may expand in C2; large/deep opposing run usually waits C3 | No source-derived shallow/deep resolver; V3 uses risk/range thresholds instead | MISSING/SOURCE_CONFLICT | Numeric geometry is not an authorized substitute for wick context |
| C3 definition | Used when C2 fails required closure; C3 closure/engulf and continuation logic depends on C2/C3 sequence and context | One hard-coded body-close resolver | PARTIAL | Current C3 is not a complete representation of source variants/context |
| POI before confirmation | C2/C3 closure and continuation are evaluated at POI; modern hierarchy FVG -> swing high/low -> CISD retest | `important_level` effectively previous H4 extreme; no full POI resolver | MISSING | Major fidelity gap; valid FVG/swing/CISD-retest setups can be missed and invalid extreme-only setups can be admitted |
| CISD | Close through opening price of opposing candle series confirms delivery shift | Opposing series + close through first series open implemented | MATCH/PARTIAL | Core formula matches, but sequence handling is narrower than source framework |
| CISD sequence persistence | Source requires close through the relevant opposing series; does not state the series becomes invalid on first non-opposing candle that fails confirmation | Current protected-swing scanner resets series after the first non-opposing bar regardless of confirmation | QORE_ADDITION | Can miss later valid CISD confirmations |
| Protected swing types | Valid from liquidity sweep or FVG reaction | Current scanner requires sweep of one supplied important level | MISSING | FVG-created protected swings are absent |
| Protected swing selection | Swing must make structural sense; EQ/context matters; closest is not always correct | `FARTHEST_STRUCTURAL` chosen mechanically | PARTIAL/QORE_ADDITION | Mechanical distance is not the author's selection rule |
| Let wick form, trade body | Wick/protected swing should form before standard continuation execution | V3/D1 only evaluates completed prior H4 then enters at next H4 open | PARTIAL | Captures positional entry case but misses same-C2 body expansion and intra-candle continuation |
| Standard continuation entry | After POI + CISD, enter on continuation closure or retest; positional entry is optional advanced execution | Positional new-H4-open execution is effectively mandatory | SOURCE_CONFLICT | Strong frequency loss; author explicitly says positional entries do not replace standard entries |
| Positional entry | Allowed only after completed fractal model and valid protected swing | Implemented at new H4 open | MATCH as optional technique, CONFLICT as universal technique | Keep as one execution path, not the only path |
| Initial target | 2026 Fractal Model material uses initial 2R with optional HTF objectives; original H4 lesson objectives are contextual | V3 hardcodes 2.5R | QORE_ADDITION | Economic distribution is not source-identical |
| Lifecycle | Context/HTF objectives; no universal one-H4 forced exit established | Forced next-H4-boundary lifecycle | QORE_ADDITION | May truncate source-valid expansions or alter losses/wins |
| Daily uniqueness | Source framework permits repeated continuations/new protected swings as structure develops | More than one raw signal per market/day causes all of that day to be discarded | QORE_ADDITION | Direct artificial frequency suppression |
| Geometry gate | No universal `risk >= 0.30%` or `closure range >= 1.2x reference` rule | Both are mandatory | QORE_ADDITION | Largest measured pre-D1 rejection gate; cannot be called source fidelity |
| Relative strength / SMT | Compare correlated assets via real SMT structural divergence; if no SMT use structural separation, then closure quality; refinement only | D1 requires exactly 2 simultaneous same-side strategy signals and 0 opposite | SOURCE_CONFLICT | D1 count is not SMT and incorrectly turns confluence into hard foundation |
| Instrument selection | Long stronger / short weaker correlated asset | D1 can retain two same-side markets rather than selecting strongest/weakest by structure | PARTIAL/CONFLICT | Does not implement author's market-selection purpose |
| Feed | Author examples and SMT are futures-oriented (e.g. NQ/ES) | Index research uses broker CFD proxies | PARTIAL | Exact sweeps, closes and SMT can differ by feed; parity should be verified against futures data |
| Stop/invalidation | Protected-swing extreme is structural invalidation | Protected-swing extreme stop | MATCH | Keep; no arbitrary buffer |

## Current measured frequency loss (diagnostic only)

Official Phase E census run `35047676664`, artifact `10427932164`, SHA `861c5a374ec92e43363303aec9ec0b01a50e7bd6`:

- 2022–23: 2,322 H4 decisions -> 142 raw structural signals -> 54 geometry-admitted -> 52 after geometry + daily uniqueness.
- 2023–24: 2,106 decisions -> 153 raw structural signals -> 44 geometry-admitted -> 42 after geometry + daily uniqueness.
- 2024–26: 4,839 decisions -> 333 raw structural signals -> 94 geometry-admitted -> 90 after geometry + daily uniqueness.

Across all three consumed windows: 628 raw structural signals versus 184 admitted by geometry + daily uniqueness (~29.3% retained) before D1's relative-strength gate. Geometry rejects 436/628 (~69.4%) of raw structural signals. This is diagnostic frequency evidence, not proof that rejected trades would be profitable.

D1 then wraps the V3 base and applies `same_side_structural_signals == 2` and `opposite == 0`, reducing the hardened sample further to 73. That rule is a QORE proxy, not author-defined SMT.

## Source-faithful correction priorities

P0 corrections should be performed before opening any new holdout:

1. Reconstruct the full author state machine: context/bias -> source POI -> wick/manipulation state -> C2-or-C3 closure -> LTF CISD/protected swing -> continuation -> execution.
2. Replace V3 numeric geometry admission with source-observable structural states. Do not invent a numerical shallow/deep threshold.
3. Implement the source POI hierarchy and preserve POI provenance.
4. Implement both protected-swing families: sweep-based and FVG-reaction-based.
5. Correct CISD sequence handling so a source-valid opposing series is not discarded by an undocumented reset rule.
6. Treat positional entry as one execution path; restore standard intra-candle continuation closure/retest execution after wick confirmation.
7. Implement true pairwise/correlated-market relative strength: SMT first, separation second, closure conviction third; use it to select the stronger LONG / weaker SHORT market rather than require an arbitrary simultaneous-signal count.
8. Restore source timing coverage for research, especially 14:00 and the complete futures H4 family where data permits; distinguish context anchors from executable trade opportunities.
9. Re-evaluate target/lifecycle separately: 2R/HTF-objective behavior must not silently remain a 2.5R + one-H4 QORE policy if the candidate is labelled source-faithful.
10. Compare NQ/ES/YM futures structure against NAS100/SP500/US30 broker proxies before certifying sweep/SMT parity.

## Governance

This audit does not select a profitable variant and does not authorize the 2020–2022 holdout. All corrections must be specified from source before economic measurement. D1 remains a useful robustness benchmark, not the final source-faithful VT-08 Index candidate.

- consumed_evidence_only: TRUE
- fresh_holdout_2020_2022: SEALED
- candidate_freeze_permitted_from_this_audit: FALSE
- LIVE_AUTHORIZED: FALSE
- REAL_CAPITAL_AUTHORIZED: FALSE
- PRODUCTION_AUTHORIZED: FALSE
- no merge without owner order
