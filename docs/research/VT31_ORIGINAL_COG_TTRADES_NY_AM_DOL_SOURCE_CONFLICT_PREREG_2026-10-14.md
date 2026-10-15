# VT31 — Original COG NY AM vs TTrades source DOL: prereg qualitative divergence

**Before new implementation and before CI.** Owner orders certify VT31 by methodology and cognition, not profits, win rate, backtests or metric thresholds. This is a **source-doctrine behavior confrontation** with original G3 COG, not tuning.

## Single predeclared synthetic counterexample
1. Prior Friday complete NY cash session 390 M1 has confirmed HIGH=150 LOW=80 (available before Monday). This is a legitimate alternative DOL in ICT-GENERAL under QORE, but NOT the specific required TTrades NY AM target.
2. Monday 00:00–09:59 NY 600 M1 continuously closed. During 09:00–09:59 the frozen H1 high=110 and low=90, otherwise baseline high 102/low98. A pivot high=104 is confirmed at 09:59 via neighbor after its 09:57 candle. The local 09h H1 extremes are both known at 10:00.
3. Monday 10:00 M1 flat; 10:01 candle breaches LOW H1=90 to 89 (first & only raid), 10:02 M1 returns and closes LONG above pivot=104, at close=105, directional and displacement. The setup is observable as-of 10:03 NY. No later M1 available.
4. Original `VT31CleanroomCognition` must be fed previous 390 bars then all current-day closed bars in chronological order, queried at exact last M1 close with `SessionId.NY_AM`. Its action, draw target/family and source provenance are taken **unaltered**.
5. Independent `native_ttrades_am_context` on exact 09 and 10 current M1 should say LOW RAID → LONG and opposite H1 09 HIGH=110, `RETURN_INSIDE_OBSERVED`; independent `inspect_cog_evidence` should not call COG source-conformant if actual `draw_target != 110`. The diagnostic will publish observed contradiction rather than modify engine or choose whichever is profitable.
6. No assumed author MSS pivot threshold: original G3 1.25×median 5 and latest confirmed 3 M1 is a QORE proxy; both 10 AM and 09 AM source M1 are synthetic, not proof of author example. The source-requirement mismatch is restricted to **TTRADES_NY_AM_2025**, not universal ICT_GENERAL_2023.

## Falsification criteria and exclusions
- If original COG has no decision, emit `ORIGINAL_COG_NO_NATIVE_NYAM_DECISION` and **do not forge a DTO**; log missing and source-observer independently. If its DOL is 150 and TTrades H1 opposite 110, emit `AUTHOR_PROFILE_DOL_DIVERGENCE` and mark TTrades method conformance false without judging ICT-general logic. If DOL is 110, note match for this scenario only, not method certification.
- Test reason `DOL_NOT_OPPOSITE_9AM_H1_EXTREME` through independent V2 if possible. One counterexample can falsify equivalence claim, but not fully certify the alternative.
- Both summer EDT and winter EST mirror contexts optional only if structurally identical as prereg. Mandatory original winter first counterexample, no scanning market corpus or choosing favorable days.
- Do not call economic backtester, no cash, PF, DD, Sharpe, sizing, bid/ask, OMS, order, OOS, LIVE. Frozen G3 original Git blobs `cognition=d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`, `operations=0ce9707314aecb71155de8b57044b6ec028847b2`, `acta=e99c70b4e018d626fb620d9a21b9314a51abc36d`; full audit JSON and human review required before any `CERTIFICADO_METODOLOGIA` or `CERTIFICADO_COGNITIVA`.

**Result remains methodology pending and cognition pending even if new code passes all tests.**