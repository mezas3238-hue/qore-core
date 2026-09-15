# Turtle Soup Candidate R1 — Development Economic & Walk-Forward Freeze

Status: **FROZEN BEFORE ECONOMIC OUTCOMES**

Research identity: `turtle-soup-candidate-r1`

Canonical trader code: `CODE_UNASSIGNED`

This document freezes the development economic screen and walk-forward protocol before any valid Turtle Soup R1 economic outcome is inspected. It grants no DEMO, LIVE, production, FTMO, FundedNext, or real-capital authority.

## 1. Immutable data boundary

Development universe is fixed to:

- EURUSD
- GBPUSD
- USDJPY
- AUDUSD
- USDCAD
- GBPJPY
- AUDJPY

Source signal evidence is provider-native cTrader D1. Causal execution evidence is provider-native cTrader M15.

Only corrected post-window-repair evidence is admissible:

- D1 workflow run `34947549114`
- M15 workflow run `34947548876`
- acquisition software SHA `5a228511d39dabd9686c2d9c14c1a6a4f52ad2b2`

The independent fresh-OOS embargo remains closed at:

`2026-03-01T00:00:00Z`

No bar with `opened_at >= 2026-03-01T00:00:00Z` may enter setup detection, fill resolution, management, metrics, policy ranking, market selection, or development walk-forward decisions.

D1 sessions are normalized from each provider-native D1 open to the next provider-native D1 open. No missing source session may be synthesized, merged, interpolated, or forward-filled. M15 execution paths must be chronological and contiguous inside the exact source session; otherwise the affected evaluation fails closed/censors rather than fabricating event order.

## 2. Frozen source configuration

Classic and Plus One retain the source-bound R1 configuration already committed:

- lookback: 20
- Classic minimum reference age: 4
- Plus One minimum reference age: 3
- Classic daily entry offset: **5 ticks**
- tick size: provider minimum price increment derived from `symbol_digits` (`10^-digits`) for this spot-FX development corpus

The source-authorized 5–10 tick Classic band is **not** optimized after outcomes. Five ticks is the frozen R1 choice.

## 3. Frozen management candidates

All ten predeclared `QORE_EXPERIMENTAL_MANAGEMENT` policies are evaluated exactly as committed; no management parameter may be changed after outcomes.

Classic:

- `C_TRAIL1_H3`
- `C_TRAIL2_H3`
- `C_TRAIL1_H6`
- `C_TRAIL2_H6`

Plus One:

- `P_B2_F50_TRAIL1_H10`
- `P_B2_F50_TRAIL2_H10`
- `P_B4_F50_TRAIL1_H10`
- `P_B4_F50_TRAIL2_H10`
- `P_B6_F50_TRAIL1_H10`
- `P_B6_F50_TRAIL2_H10`

No policy receives fold-specific tuning.

## 4. Frozen cost model

Primary development transaction cost:

- `1.0 bp` total round-trip notional cost per full-position trade.

Stress transaction cost:

- `2.0 bp` total round-trip notional cost per full-position trade.

Cost is deterministic and expressed in R using initial source stop risk. For a full-position trade, price-cost is `entry_price * bps / 10_000`; partial exits do not create or remove exposure-dependent cost hindsight — the full round-trip cost is charged once per completed trade. Censored trades do not claim realized P&L.

These are QORE research cost assumptions, not claims about author source rules or final FTMO/FundedNext execution costs. Prop-firm-specific execution qualification remains a later gate.

## 5. Development walk-forward partitions

The walk-forward is expanding-window and chronological. The ten fixed policies are not selected or tuned inside a fold. Each fold is an untouched forward slice relative to all preceding development evidence.

| Fold | Expanding training evidence available before | Forward test window |
| --- | --- | --- |
| WF1 | `< 2024-09-01T00:00:00Z` | `2024-09-01T00:00:00Z` → `< 2024-12-01T00:00:00Z` |
| WF2 | `< 2024-12-01T00:00:00Z` | `2024-12-01T00:00:00Z` → `< 2025-03-01T00:00:00Z` |
| WF3 | `< 2025-03-01T00:00:00Z` | `2025-03-01T00:00:00Z` → `< 2025-06-01T00:00:00Z` |
| WF4 | `< 2025-06-01T00:00:00Z` | `2025-06-01T00:00:00Z` → `< 2025-09-01T00:00:00Z` |
| WF5 | `< 2025-09-01T00:00:00Z` | `2025-09-01T00:00:00Z` → `< 2025-12-01T00:00:00Z` |
| WF6 | `< 2025-12-01T00:00:00Z` | `2025-12-01T00:00:00Z` → `< 2026-03-01T00:00:00Z` |

Warm-up/history bars before a test window may be used only to causally establish a signal whose signal/fill belongs to the test window; their realized returns never migrate into the test window.

## 6. Frozen development metrics

For each policy and aggregate/per-fold/per-market/per-side views, record at minimum:

- setup, abstain, ambiguity and invalid-evidence census;
- source fills;
- management closed vs censored count;
- gross R;
- primary-cost net R;
- 2 bp stress net R;
- mean and median net R;
- win rate;
- profit factor;
- max drawdown in net R;
- longest losing sequence;
- holding bars;
- market, year and side contribution concentration;
- leave-one-market-out net R.

## 7. Frozen advancement gate

A policy may advance from development characterization to candidate/config freeze only if **all** of the following are true on primary-cost results unless explicitly stated otherwise:

1. At least **30 closed trades** across the six forward folds.
2. Aggregate forward-walk net expectancy is **strictly > 0 R/trade**.
3. Aggregate forward-walk profit factor is **strictly > 1.00**.
4. At least **4 of 6** forward folds have total net R strictly greater than zero.
5. Aggregate **2.0 bp stress** expectancy is **>= 0 R/trade**.
6. Leave-one-market-out total net R remains **strictly > 0** for every one of the seven market removals.
7. No single market, calendar year, or trade side contributes more than **50% of gross positive net-R gains**. If total positive gains are zero, the policy fails.
8. No unresolved data-integrity or causal-path defect may be counted as a realized trade.

Max drawdown and losing-sequence metrics are reported at this gate but are not converted into a fixed risk-percent approval threshold here; risk sizing, prop-firm drawdown compliance, Monte Carlo, Risk Review and CIBO remain later gates.

Passing this development gate is **not approval**. It only authorizes a configuration freeze followed by the single-use fresh OOS.

## 8. Selection rule

Policies are first screened independently against the advancement gate. Failing policies are rejected; they cannot be rescued by relative ranking.

If more than one policy within a source variant passes, selection is deterministic and uses, in order:

1. higher 2 bp stress total net R;
2. higher primary-cost total net R;
3. lower max drawdown R;
4. higher minimum fold net R;
5. lexicographically smaller frozen policy ID as final deterministic tie-breaker.

Classic and Plus One are not forcibly blended. A variant with no passing policy is rejected at the development gate.

## 9. After development

Only a passing selected policy may be frozen with its exact source-config fingerprint, management-policy fingerprint, seven-market universe, cost/execution model identity, corrected dataset digests, software SHA and walk-forward protocol. Only after that freeze may evidence on/after `2026-03-01T00:00:00Z` be opened once for fresh OOS.

After fresh OOS release there is no retuning of entry offset, management policy, partial schedule, trail lookback, hard exit, market universe, cost model, walk-forward thresholds or selection rule.