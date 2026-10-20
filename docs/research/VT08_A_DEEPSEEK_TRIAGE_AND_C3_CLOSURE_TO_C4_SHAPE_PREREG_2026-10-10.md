# P0 VT08 — SOURCE-TRIAGE DEEPSEEK Y PRERREGISTRO C3 CLOSURE→C4 SHAPE V1
Fecha 2026-10-10 · Architect A · PR #765 · Issues #762 / #763 · 1095D CONSUMIDO · 7Y SEALED intacto.

## Auditoría del informe recibido de DeepSeek Expert

Fuente principal TTrades:
- https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/ (2025-12-03)
- https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/ (2026)
- https://ttrades.com/how-to-trade-candle-3-in-the-fractal-model/ (2025-09-06)
- https://ttrades.com/easy-daily-bias-a-mechanical-trading-framework/ (2025-12-13)
- https://ttrades.com/using-equilibrium-in-continuations/ (2025-08-02)
- https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/ (2026-10-10; **aclaración posterior**, no fuente retroactiva de 2025)
- https://ttrades.com/how-to-trade-candle-2-ttrades-fractal-model/ (2025-08-16)

**A — fuente literal verificada (con matices)**:
1. C2 reversal closure = C2 sweeps C1 extreme and closes back in C1; C3 closure distinto: when C2 fails, C3 closes over/below C2 body without sweeping C2 high/low; then expect C4. C3 must be **CLOSED** before C4 is contemplated. A C3 close through C2 body alone does not verify POI or CISD; the author exige swing formed at POI with closure.
2. C3 continuation after fully reversed C2 with large wick, valid POIs FVG, High, Low; CISD/PS confirm causal LTF; user report's claim "C3 must close outside C2 range before enter C3" would use future information to enter C3 and **IS REJECTED**.
3. Daily EQ continuation can use prior day's wick-to-wick EQ as upper/lower half and requires **directional premise + POI + candle closure + CISD**. EQ does not turn all B01 UNRESOLVED into trades by itself.
4. **Updated author October 10 2026:** C2 EQ on full candle if closes WITH the swing point; on close-to-extreme wick when closes AGAINST swing; C3 EQ full candle. The report's blanket `(high+low)/2` for all candles **contradicts this update**.
5. Original 01/05/09 NY Owner clocks must remain NY-local across DST, not jump 01→02 NY. Timezone offset UTC changes.

**C — unresolved formalizations falsely dressed as A**:
- `small wick <=50%`, `large >50%`: numerical ratio NOT demonstrated in text.
- `CISD timeout=8 M15`, `after H4+2 M15` entry expiry, nearest protected swing, every signal next-M15 OPEN, stop in candle body, fixed TP: context-specific or QORE conjecture, NO source approval.
- `C3 closure→C4 entry exactly at EQ`: source says C4 forms a wick into its appropriate half, THEN LTF displacement and refined entry; EQ itself not limit fill.
- `+200-300`, `+100-150`, `20%-35%` opportunity capture: numerical predictions fabricated absent measure, do not prereg as outcomes.
- Example C2 swept high with bullish CISD incorrectly labels bearish reversal and example C3 suggests entry after C3 closes in that SAME C3; invalid.
- TTrades warns CISD without HTF C2/C3 closure invalid (https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/). The previous 1514 intracycle V1 was anyway PF/DD rejected; do not re-authorize by citing DeepSeek.

## New hypothesis BEFORE any C3 counts

**Research bundle:** `C3_CLOSURE_TO_C4_M15_SOURCE_SHAPE_V1` is **SHAPE_ONLY**.
**No PnL, no trades and no labels SOURCE_COMPLETE**. Original evidence 1095d 5 markets, exact data SHA `b2d33e1b4829d8b4afc76983decca8a99131403c`.

C1 = H4 reference ending at the start of C2, C2 prior H4 (-4h to anchor), C3 current Owner NY H4 (anchor to anchor+4h). Do not inspect C3 completed before anchor+4h. For classification, enumerate C2 incomplete-reversal-closure (both `C2 did not sweep C1` and `C2 swept but failed return-inside`), keeping them separate.

C3 continuation/reversal-closure geometry:
- `close_above_C2_body` if C3 close > max(C2 open, C2 close); bearish analog < min(C2 open, close). Must not sweep either C2 high or low: C3 high<=C2.high and C3.low>=C2.low. Count per side, optional stronger `body_engulf` requiring C3 open below/above opposite C2 body bound. These are distinct stats; **not claim source rule fully proved by body-close alone**.
- Unresolved POI/PS must be counters. Count separately cases with C3 closed LTF CISD/PS anchored to C2 high/low and recent protected swing, and cases with source bias aligned; absence of a demonstrated actual significant POI means **NO executable signal**.
- Next C4 is the H4 beginning after C3 close. `C4_WITHIN_OWNER_ANCHORS` only if its local NY opening hour is in 01/05/09; no 13NY. Never advance C3 close to earlier decision.
- Mark full C3 wick-to-wick EQ as of completed C3; C4 first M15 closed bars may be used to measure EQ-half respected / violated **observational only**, no entries.
- Count by year/market/source failure, C2 state, C3 close-body geometry, complete vs incomplete M15, C4 owner allowed vs forbidden, C3 LTF PS proof, C4 first-M15 EQ. No ex-post performance selection, no arbitrary >80 candidates threshold.
- `source_event_id` across future WAIT must derive only from market+cycle+side+POI/origin, not later result, and NO EventV1 issuance at this stage.

Negative adversarial tests: C3 close before 4h forbidden, C3 sweeps either C2 extreme rejected for this subfamily, equality not a strict body close, no future C4 priced as C3 entry, C4 13NY forbidden; DST NY anchor stable 01/05/09, future bars not used to validate C3 closure.

**Prereq for SOURCE_COMPLETE:** identify valid POI, source-compatible C2/C3 closure case, LTF CISD/PS timing, C4 wick/EQ behavior and fill/TP/SL/lifecycle backed by original author; B must reconstruct cognitive feature provenance, bilateral manifest. Sealed 7Y untouched.
