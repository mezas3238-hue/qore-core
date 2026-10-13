# QORE-Alpha 2 — TSMOM-D1 daily momentum 252 sessions / five-session exit: first signed gross test result

**Date** 2026-10-12. **Experiment** ONE fixed canonical TSMOM at daily/multi-day scale, not optimization W1/2/3. **Verdict:** `TSMOM_EXPLORATORY_GROSS_SCREEN_FAIL`. This is **NOT** a failure of all TSMOM models and **NOT** a NET or live execution test.

## Verifiable evidence chain

- **Pre-outcome frozen scientific protocol:** [QORE_ALPHA2_TSMOM_DAILY_WEEKLY_SINGLE_TEST_PREREG_2026-10-12.md](QORE_ALPHA2_TSMOM_DAILY_WEEKLY_SINGLE_TEST_PREREG_2026-10-12.md), **ancestor commit `1c46194e3b5e9165504f0ff9d41eb1dee57f0b42`**. The protocol was published before this daily-timeframe strategy's original M5 outcomes were read; 2016–2024 market history had been studied previously by QORE, so this is **EXPLORATORY REUSE**, not independent OOS.
- **Original computation:** [Actions #38317398724](https://github.com/mezas3238-hue/qore-core/actions/runs/38317398724), HEAD exact `af3ef792f972bc5ec00e1419f6ea917c16624d65`, **35/35 jobs SUCCESS** (1 preflight + 12 Original Atlas SHA/worker + 21 New ICMarkets SHA/worker + 1 all33 gross panel); Ruff + **19/19 synthetic tests**. All 33/33 source audit workers finished successfully; 11-year original RAW+QUALITY and final33 manifest checked before opening pre-embargo price values. No 2024-09-17+ price bytes opened.
- **Signed raw result:** GitHub Actions panel artifact **#11777507376**, ZIP SHA256 **`a907e980adab2484959ee000d0836d3fb0af8ca4090b674435ff10ee8de83b6f`**, ZIP verified independently after retrieval and both `OUTPUT_SHA256SUMS.txt` entries (panel JSON and exact head) matched. Machine file `alpha2-tsmom-33-weekly-gross-exploratory-panel.json` is inside that artifact, no original M5 raw ZIP copied to PR or report.

## Method actually tested (NOT changed after outcomes)

Every original symbol uses previous 252 eligible UTC day closes as a trend signal; one first eligible source-week decision, reference entry at **first native M5 OPEN** after a midnight UTC decision, reference exit at **last native M5 CLOSE of the fifth eligible source session**, fixed signed 5-session momentum comparator. Missing/sparse days not filled, trades crossing DEV/DIAG or 2024 embargo censored. The weekly calendar portfolio divides each actual source price-return bps by all **33** slots (flat weeks remain zero); circular synchronized four-week block bootstrap, 2,000 draws with seed 20261012. Macro/news PIT, account/CFD identity, actual execution BID/ASK, commissions, swaps, spread, and financing all remain **unknown**; numbers below are **gross reference bps only**, not effective broker contract PnL.

## Results — true all33 sources, two eras

| Metric | DEV 2016-09-17—2022-09-17 | DIAG 2022-09-17—2024-09-17 |
|---|---:|---:|
| Original reference events | **8,626** | **3,427** |
| Active calendar weeks | **263** | **104** |
| Total calendar weeks (include no exposure) | 314 | 106 |
| Weeks sample gate | PASS (min 52) | PASS (min 26) |
| Mean gross reference bps per strategy event | **+0.92575** | **−3.79109** |
| Mean weekly all-33 slot equal-weight gross reference bps | **+0.77065** | **−3.71414** |
| CI95 4week synchronized bootstrap, weekly gross | **[−4.11963, +5.51418]** | **[−16.88710, +6.42872]** |
| Weekly paired strategy minus 5d control (bps) | **−0.28995** | **−6.38034** |
| CI95 bootstrap, paired weekly delta | **[−6.48514, +5.64560]** | **[−23.86431, +6.85015]** |
| Opposing predictions strategy/control | 3,769 (43.69%) | 1,566 (45.70%) |
| Original12 cohort gross mean per event | +3.79692bps / 3,130 | −1.18315bps / 1,243 |
| New21 cohort gross mean per event | −0.70940bps / 5,496 | −5.27537bps / 2,184 |

**Total: 12,053 strategy reference events from 33 symbols; 367 occupied calendar weeks across the periods, not 12,053 independent statistical observations.**

### Year diagnostics, descriptive ONLY — no winner selection

- DEV annual average per-trade gross: 2017 +5.7834bps (557), 2018 −0.9673bps (1716), 2019 −4.6349bps (1715), 2020 +3.5139bps (1714), 2021 −1.5571bps (1712), first 2022 +9.0890bps (1212).
- DIAG annual average per-trade gross: late 2022 **−35.1330bps (495)**, 2023 +1.6061bps (1716), 2024 to 2024-09-17 +1.3509bps (1216).
- **Do NOT exclude the negative 2022 to turn the result green.** The combined predeclared two-era gate fails. Observed source-cohort asymmetry is NOT actionable without account contract equality and confidence/instrument-level economic analysis.

### Cost sensitivity (hypothetical only, NOT spread/NET)

DEV reference mean/event +0.92575bps: even an *assumed* round-trip 1bps would bring it to **−0.07425bps**. DIAG is already **−3.79109bps** with zero assumed fees and becomes more negative with positive assumptions. This is an illustrative subtraction, not a broker-verified cost model.

### Power and epistemic interpretation

The test overcomes earlier **raw opportunity sparsity** but the independent time variation is governed by ~263 DEV and ~104 DIAG occupied weeks, and markets correlate. Weekly 4week block-CI lower bounds are negative in both eras; the narrower DEV interval still covers positive effects up to +5.51 weekly bps, DIAG covers up to +6.43. Thus **the frozen 2-era gross-positive screening rule FAILS**; this does **not** exclude every hypothetical 1–3bps effect, prove structural zero alpha, falsify classical TSMOM as a whole or certify negative broker PnL. Avoid IID power using 12,053 events.

### Critical causal/execution issue retained as BLOCKER

A midnight UTC decision can coincide exactly with the next day's first bar `OPEN` for markets active around UTC midnight (previous M5 ends as current M5 begins). The sign only uses completed **previous** day closes, but this does not prove a physically obtainable `OPEN` fill with nonzero compute/network latency. For other symbols first source bar may open later. The run did not preserve per-event exact first-M5-start/decision-ready timestamps or verify broker session times and tradeable quotes, so **treat reference OPEN as a potentially zero-latency non-executable price**. No retroactive one-bar delay/reoptimization on this exposed panel; future executable TSMOM research must prereg new first-available order clocks with broker-native quote evidence and fresh OOS. The all33 UTC-day session boundary is an approximation, not provider-issued daily candle-session identity.

## Program decision and next action

- **CLOSE this exact TSMOM-D1 configuration as `TSMOM_EXPLORATORY_GROSS_SCREEN_FAIL`**, without threshold/timeframe re-tuning, cohort cherry-picking, removing late-2022 or choosing positives in 2023/2024. **0/3 Alpha2 certified**.
- The owner-requested **daily/multi-day hypothesis was actually run and produced one outcome**, not another documentation-only round.
- Preserve PR #840 DRAFT and evidence in GitHub; #837 durable vault/legal restore still urgent before Atlas12 2026-12-16; #868 contract identity, #852 true BID/ASK/PIT + genuinely prospective fresh OOS remain OPEN, but do not let infrastructure displace hypothesis research.
- If investigating a distinct multi-day economic mechanism, require **new explicit independent prereg, separate prospective data/access census and power target**, not retrospective selection from this exposed 2016–2024 panel. Do not claim that failure here means all higher-horizon strategies fail.
- No orders, no demo fills, no PAPER/LIVE, no VPS/MT5/QDLE/CIBO/Shared, no main. Total UTC-001 certificates **0**.
