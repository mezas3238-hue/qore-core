# VT08 CRT THREE-SOURCE V3 — G-M4 causal lifecycle integration (preregistration)

**Date:** 2026-10-15, before running this new integrated G-M4 case replay.
**Repository:** mezas3238-hue/qore-core · **PR #626 DRAFT** · **NO MERGE, NO LIVE/DEMO/VPS, NO SIZING**. Original three-author CRT inspiration: RomeoTPT, SpeculatorFL and TraderFlameseN; the V3 exact M15 third-close body protocol is QORE ENGINEERING, **not** author-proven certified fidelity.

## Frozen input identities, without outcomes selected ex post

- Method/source: `VT08_CRT_THREE_SOURCE_QORE_V3_CSD_THIRD_CANDLE`, original Atlas AUDUSD+USDJPY M5 (296,372 candles, known DEV period, NOT new OOS). Existing V3 [causal replay #38749028744](https://github.com/mezas3238-hue/qore-core/actions/runs/38749028744) fixed 139 candidate IDs (61 AUDUSD/78 USDJPY).
- Existing G-M3 [cognitive source replay #38750815066](https://github.com/mezas3238-hue/qore-core/actions/runs/38750815066) recognized all 139 source confirmations and **ABSTAIN 139/139** because methodology composite not independently closed.
- Only after source/cognitive decision time, existing [price-path replay #38749761117](https://github.com/mezas3238-hue/qore-core/actions/runs/38749761117) observes one of six **price-only** terminal/unknown categories. Previously fixed: destination-first 23, invalidation-first 69, expire-no-touch 42, unknown 5; these do NOT become orders or economic gains.

## New G-M4 obligations (READ-ONLY research lifecycle, NOT PASS)

1. One immutable event key `source_event_id`, market, UTC `decision_clock`, `H4_C3_open` must match in the separate source, cognition and price registries. Deny duplicate IDs, forged attestations, any permission to execute, any exposure/lot/capital/PnL values.
2. Build **causal stage chain at decision time**:
   `OBSERVED_EVENT -> HYPOTHESIS_FORMING -> AWAITING_CONFIRMATION -> CONFIRMED` using QORE `transition_hypothesis`. Reconstruct original G-M3 positive recognition and `reason()`, preserve `ABSTAIN` + `CRT_SOURCE_STRATEGY_NOT_CLOSED`. Query actual `present_vt08_gm5_status()` and `current_three_source_methodology()` for read-only router lock. **Do not substitute a mock all-PASS Boolean**, do not call broker/CIBO trading APIs.
3. **Only after clock of decision** may observe subsequent M5 price lifecycle. This is post-decision **research observation**, NEVER input to create/change the initial hypothesis/cognitive response. If first M5 opened at T touches boundary, its completed-candle evidence is known at **T+5 minutes**, never T. Reject any hit timestamp before decision, or timestamp+5m beyond parent H4 C3 close. No causal event may be revived, rearmed or switched to another hypothesis after invalidation.
4. `INVALIDATION_FIRST`/ambiguous simultaneous M5: `CONFIRMED -> THESIS_INVALIDATED -> THESIS_KILLED`, explicitly annotate falsification; ambiguous never relabel destination.
5. `DESTINATION_FIRST`: `CONFIRMED -> THESIS_KILLED`, destination consumed and source identity remains immutable. This is a **price** observation, not profit or trade.
6. `EXPIRED_WITHOUT_TOUCH` (or last-bar H4 expiry): `CONFIRMED -> THESIS_KILLED` **at end of H4 C3**, not retroactively at initial decision.
7. `UNKNOWN_*`: leave causal hypothesis `CONFIRMED` **with terminal status unknown/not proven** in the laboratory record, never invent a successful or unsuccessful price touch. It has **no execution authority** and cannot auto-rearm (an operational controller must expire it when validated clock data exist). Flag unresolved G-M4 barrier, not G-M4 PASS.
8. Assert all 139 source IDs reconciled with each phase, no multiplication of trades; keep market/year/outcome denominators and explicit `no_sizing`, `no_PnL`, `not_fresh_OOS`, `G_M4_PASS=False`.
9. Tests: matched positive, mismatched event ID/direction/decision clock, forbidden future field, invalid transitions, expiry clock, same-M5 invalidation, unknown, no duplicate event, no fake G-M5 approval; mutation in post-decision prices may change **terminal** but must never change source/cognitive record at decision.
10. This stage's **CI SUCCESS validates invariants and scientific readiness only**. G-M4 actual PASS requires independently adjudicated three-source QORE rules, authoritative full E2E/position semantics with Risk/CIBO handoff, clocks/session/PD array and signatures. Global PF/DD/Sharpe/Sortino/OOS/WFO/Monte Carlo/stress remain untested; capital DD computations only in CIBO/Risk independent of trader sizing. Original Atlas 2024–2026 already seen: not a fresh holdout.

**Additional problem revealed by design:** price-only lifecycle's UNKNOWN state cannot be interpreted as price success, nor can a CONFIRMED source with a missing M5 path be closed scientifically without extra evidence. G-M4 must explicitly report such censored cases, not fabricate a completed lifecycle to reach "100% PASS".
