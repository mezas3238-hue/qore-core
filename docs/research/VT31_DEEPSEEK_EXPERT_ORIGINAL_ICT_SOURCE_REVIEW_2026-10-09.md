# VT31 — DeepSeek Expert review against the actual 2023 ICT primary Silver Bullet lecture

**2026-10-09 · Architecture OPS / source verification.**  
**Priority:** Original Silver Bullet fidelity (not merely TTrades interpretation), then economic full-Core certification.  
**Primary author and documentary authority:** Michael J. Huddleston / The Inner Circle Trader, [2023 ICT Mentorship — ICT Silver Bullet Time Based Trading Model, 2023-05-14](https://www.youtube.com/watch?v=tRq1hyGGtl4).  
**Independent time-indexed transcript used for audit:** [full lesson transcript](https://info.quagmyre.com/xwiki/bin/view/Forex/The-Inner-Circle-Trader/ICT-Youtube-Series-2023/ICT-YT-2023-05-15-ICT-Mentorship-ICT-Silver-Bullet-Time-Based-Trading-Model/?xpage=print). NOTE: machine transcripts can mistranscribe jargon; video remains canonical, and the DeepSeek reply is a SECONDARY interpretation, not a source of truth.

## 1. What can be confirmed directly from the original source

| Source element | Original lecture evidence | Disposition in VT31 |
|---|---|---|
| Three source windows, US DST | ~09:00-09:35 London 03-04 NY; ~12:38-14:05 NY AM 10-11; ~14:05-14:23 NY PM 14-15. Chart must use local New York timezone. | CONFIRMED, `vt31_london_session_contract_v1.py` implemented/tested. No fixed Europe/London hour. |
| DOL leads, entry precision secondary | ~03:57-08:10: PDH/PDL, preceding session/week high/low, NWOG, inefficiencies, and possible OTE-type setups; no single mandatory PDH. | CONFIRMED. Require independent causal `next_draw_on_liquidity`, not nearest level by distance alone. |
| Potential *framework* >=10 index points / 40 index futures ticks; >=15 FX pips | ~00:40-02:15: projected best-case movement, explicitly NOT required capture or realized entry-to-exit 10 points. | CONFIRMED. Research NAS100 point mapping must still be checked against broker's index conventions. |
| Classic FVG forming in source hour | ~09:20-11:35 / 13:00-14:00 / 14:35-15:40: source-specific FVG and direction aligned to DOL. | CONFIRMED as necessary methodology focus; complete candle and earliest identity formalizations separately classified. |
| Structural shift | ~10:15-10:30 London **example**, ~14:35-14:50 NY PM **example**. | CONFIRMED as featured execution context, but cannot quote this 19-minute source alone as a logically universal MSS mandate in every conceivable Silver Bullet. COG MSS causal producer still needed in rigorous formalization. |
| First FVG | ~15:20-15:40 NY PM says first gap *inside entry prices* (suitable price zone), **not indiscriminately first raw FVG of any side for the entire hour**. | VERIFIED qualified-source precedence. COG must establish direction and entry price zone BEFORE the first suitable gap is selected. |
| Source formation and entry inside hour, position can remain open after | ~11:20-11:55 and ~13:35-14:05. | CONFIRMED. Expire prospective new entry at end, do not auto-liquidate an already filled trade then. |

## 2. Expert statements NOT proven as unconditional ICT source rules

- **“CE 50% as the ONLY valid entry”**: conservative comparison policy, not guaranteed universal from this 19-minute lesson, which shows entry *inside* the gap. Backtest center vs alternatives separately without relabeling one as literal ICT doctrine.
- **“First FVG of entire hour, ignoring all later”**: misstates the lecture's *first suitable FVG inside entry prices* emphasis. A raw gap against the DOL or outside entry zone must not preempt the first correct directional gap.
- **“MSS is mandatory in every possible Silver Bullet”**: MSS is in examples and central structural interpretation, but absolute universality not independently proven from 2023 main video. For safety, research candidate currently requires causal externally produced MSS. Label the requirement QORE conservative formalization where not directly quoted.
- **“All three 1-minute FVG candles MUST originate inside the hour”**: operationally reasonable *strict comparison* policy, but original lecture says the FVG *forms* in hour; does not unambiguously timestamp the first candle for every timeframe. Test both variants and preserve this source distinction.
- **“Stop MUST be at the extreme of candle #1”**, **“entry MUST use CE”**, **“50/25/25 partials with immediate breakeven”**, **fixed 10:00-10:15/10:15-10:45 phase splits**, and **“exit all positions at next session/no progress”**: not certified from the primary Silver Bullet lecture. Stop, broker buffers, partials and management require separately evidenced QORE operating policy and tests.
- **“Sweep of 09-10 always required”**: TTrades derivative, NOT ICT's universal source rule. Conversely, the original lecture does not supply the simplistic proposition that *every* no-sweep FVG is a valid setup.
- **“55/3Y is a 0.07% setup rate”**: denominator error. The 55 admitted trades belong to one NY AM stream with 769 eligible NY sessions, **55/769 = approximately 7.15%**; do not divide by three independent source windows that the old NY control never traded.
- **“22/55 definitely not ICT trades”**: signal-time FVG absence is not fill-time FVG absence; must reconstruct actual pending lifecycle and see whether an authentic first chosen gap matures BEFORE the real fill. No deleting 22 trades by terminal result.
- **“The ICT original must turn profitable, density 200–400 guaranteed”**: unverifiable prediction, not certification. No no-lookahead 3Y source-true execution replay yet exists.

## 3. ACTUAL OPS code and green scientific tests produced after this expert consultation

### P0 Original ICT candidate chronological state machine — GREEN

- Code: `src/qore/infrastructure/traders/vt31_ict_silver_bullet_causal_state_v1.py`.
- CI: [original causal FSM run 38011001413](https://github.com/mezas3238-hue/qore-core/actions/runs/38011001413), SUCCESS, measured SHA `b13aa47417b174bc77de71abe59e1432185752e9`.
- Session-aware `America/New_York` 03–04 / 10–11 / 14–15 and DST tests.
- Accepts explicit externally supplied **immutable causal DOL + MSS**, both with prior producer/observation timestamps. Cannot choose direction from eventual outcome.
- Consumes **strict chronological previously closed M1**; refuses duplicate, missing or future candles; cognition must follow exact current closed M1 event (no backdating of future events).
- Finds first **suitable directional** FVG in chosen DOL direction, with research formalization of all three closed source M1 inside window; projected >=10 NAS100 index points toward target, midpoint CE and illustrative stop candidate.
- Emits `WAITING_FOR_EVIDENCE`, `WAITING_FOR_FIRST_SUITABLE_FVG`, `PENDING_RESEARCH`, `RESEARCH_MIDPOINT_TOUCH_NOT_FILL`, `AMBIGUOUS_TOUCH_AND_INVALIDATION`, `SOURCE_INVALIDATED`, `WINDOW_EXPIRED`.
- Explicitly labels CE, full-three-candle boundary, stop reference as **QORE_RESEARCH_FORMALIZATION**. DOES NOT place orders, infer MT5 broker fill from M1 wick touches or claim COG route, performance, certification. Same-bar CE touch and invalidation are explicitly ambiguous.
- Synthetic self-tests cover candidate formation, direct source provenance, winner-independent first-gap immutability, US/UK DST, opposite-side DOL/MSS, out-of-order M1, no backdated cognition, same-minute invalidation vs wick-touch ambiguity.

### P0 Source preadmission contract corrected — GREEN

- Code: `src/qore/infrastructure/traders/vt31_ict_silver_bullet_source_contract_v1.py`.
- CI: [run 38010971276](https://github.com/mezas3238-hue/qore-core/actions/runs/38010971276), SUCCESS, measured SHA `1a6a712b3e6e1fc4e1433935e9a437167e0eb024`.
- Research gate now explicitly distinguishes source-hour FVG third close from **straddling 09:59/10:00**, labeling the cross-hour veto as QORE research policy not ICT proven universal.
- New **same-timestamp-or-earlier M1 pseudo-fill** barrier: the exact close instant cannot be claimed an MT5 fill without tick sequence evidence.
- Existing COG/NY production or actual 55-trade baseline **NOT modified**.

### P0 Full frozen 3Y FVG source-boundary attribution — GREEN

- Script: `scripts/vt31_ict_silver_bullet_3y_source_fidelity_probe_v1.py`, full source identity + `1,059,784` M1 NAS100 candles from artifact `11459859004`.
- CI: [run 38011040314](https://github.com/mezas3238-hue/qore-core/actions/runs/38011040314), SUCCESS, measured SHA `ff7ba155ed746eb9093cf20951d7bf6e6cb919b6`.

| Source hour NY | Raw 3-M1 FVG events with third candle within hour | Full 3 M1 candles inside hour | Cross-boundary events | Complete source-hour days with >=1 inside-hour FVG |
|---|---:|---:|---:|---:|
| London 03–04 | 11,769 | **11,342** | **427** | 774 |
| NY AM 10–11 | 11,123 | **10,660** | **463** | 771 |
| NY PM 14–15 | 10,312 | **9,946** | **366** | 741 |

**Result:** the conservative all-three-in-hour policy would exclude **1,256 raw FVG observations** (427+463+366) but no covered day loses *all* its source-hour raw FVGs. This is **not** number of valid setups, nor trading performance. It proves this textual ambiguity matters operationally. Proper next step is test as independently tagged versions of the source methodology rather than silently impose one as doctrine.

## 4. Current architectural/engineering integration

- **Architect 1 / COG** owns independent cognitive DOL family selection (not PDH-only), as-of source proof, first suitable price zone and MSS/structural-break historical context. The canonical reasoning engine must act again at prospective fill M1-open T, no signal reuse or lookahead.
- **Architect 2 / OPS** owns source-qualified event/order lifecycle for both sessions, MT5 bid/ask/tick-aware fill testing, cancellation/invalidation prefill and route->execution telemetry, genuine historical economic replay.
- Existing source `vt31_silver_bullet_r2_2.py` is explicitly `TTRADES_VARIANT`; never rewrite baseline controls. Comparative original-ICT independent candidate is the legitimate next phase.
- **Frozen 55 NY control still fails**: 55 trades, PF ~1.633, DD 21.3586R vs 6R, Sharpe ~0.562, MC-positive ~81.47%. External DeepSeek claims are hypotheses, not evidence of a profitable copy.

**Certification:** NY FAIL; London NOT YET economic model; dual LOCKED; Fresh Holdout SEALED; live/funded NOT AUTHORIZED. This analysis changes source-fidelity evidence and tests only; it does not improve historical P&L by fiat.
