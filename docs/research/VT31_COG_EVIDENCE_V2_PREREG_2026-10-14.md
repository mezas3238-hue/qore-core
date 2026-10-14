# VT31 — COG_EVIDENCE_V2 causal M1 attestation prereg (2026-10-14)

**Published before V2 implementation/testing and without using returns.** PR #926 remains isolated from original G3 #896. No trader execution, sizing or production authority.

## Two bounded profiles, never combined post hoc

- TTRADES_NY_AM_2025: only 10:00–11:00 New York DST, prior 09:00–10:00 H1 exactly 60 closed M1, first raid HIGH implies SHORT or LOW implies LONG; displacement-confirmed MSS AFTER raid must close strictly INSIDE prior H1, target at opposite H1 extreme. Reuse independent source-context witness from PR #926; any disagreement is recorded, not patched to favorable cases.
- ICT_GENERAL_2023: London/NY AM/NY PM 03/10/14 local NY windows; no universal 09:00 H1 raid or opposite H1 target. Generic DOL provenance cannot be independently verified from a COG DTO alone; absent a separate independent pool witness, status UNKNOWN_DOL_PROVENANCE rather than blanket ICT-certified.
- Current QORE structural MSS uses a 3-M1 strict pivot, a confirmed break, and body at least 1.25 times the median of 5 previous M1 bodies excluding the most recent M1. These are QORE numerical proxies, not canonical statements attributed to ICT/TTrades.

## Independent structural validation using ORIGINAL real M1Bar objects

Input: explicit profile, session, external as_of timestamp, ordered closed M1 history, existing genuine CognitiveDecision or no decision. Never reconstruct a COG decision from hindsight. Check as_of equals final close, all input M1 were closed no later than as_of, timestamps strictly increasing, and DTO observed_at matches external as_of and session.

- MSS actual bar must be found at declared structure_break_confirmed_at, with full causal lookback of at least 10 bars, recent 95 bars for structural pivot candidate, and 7-bar body reference. If data is absent, label UNKNOWN, never invent a pass.
- For G3 DTO the pinned mss_anchor_close must EQUAL independently observed original M1 close; mismatch REJECTED. Legacy DTO without pinned anchor = UNKNOWN_MSS_CLOSE_NOT_PINNED even if other facts match, because it cannot establish the immutability attestation.
- Pivot actual confirmation is rightmost bar of 3 contiguous M1 around pivot; strict local high for LONG / low for SHORT. Independent comparison of pivot price and pivot confirmation close against COG DTO. The pivot must be preconfirmed strictly before MSS.
- LONG prev close <= pivot high < MSS close and bullish MSS; SHORT prev close >= pivot low > MSS close and bearish MSS. Body >= 1.25 times median of 5 closed M1 bodies at offsets [-7:-2] relative to MSS, exactly matching QORE code. Historical MSS may be revalidated at later M1; check original candle at original timestamp rather than requiring repeat MSS.
- TTrades source witness independently checks exact H1, sweeps, 10am prefix, reversal, direction, target. Bidirectional sweep inside one M1 is UNKNOWN_INTRA_M1_ORDER rather than PASS. Contradictions REJECTED, absent evidence UNKNOWN.
- Order M0-M3 result may say CONFIRMED_CAUSAL_CONTEXT but certification flags remain all false; M4 entry models, stop and execution, independent COG/OPS reviewers, and performance are separate later gates. No heuristics tuned by profit.

## Frozen QA

Test synthetic true LONG/SHORT and MSS later reuse; tampered pivot price/confirm time; MSS close mutation; nonexistent MSS or missing history; wrong direction; no actual crossing; under-threshold body; incomplete H1; double raid ambiguous; missing COG; ICT London no 9AM not rejected for 9AM requirement; DST, stale/as_of mismatch, and G3 blob integrity with existing regression tests. SUCCESS of tests proves witness engineering, NOT full method or trader certification. No changes to original paired G3 act SHA a446afa17ed6e411b8f0b6fc182b103a78959a97 and code SHA 78d4cdac0e09d1a6eef37b99c505ffc5098031fc.

**Allowed decisions**: CONFIRMED (M0-M3 causal context only), REJECTED (contradiction), UNKNOWN (missing/ambiguous). Certification NOT granted; no merge, no VPS, no LIVE, no broker fills, no holdout or lot-sizing.