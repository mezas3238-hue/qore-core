# QORE NQ AM TEMPORAL LIQUIDITY REVERSAL V1 — PRE-HOLDOUT CONTRACT

Identity: `QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V1`  
Tracker: #653  
Source video: YouTube `UVVmS0de0g0`  
Status: DEVELOPMENT / HOLDOUT SEALED

## 1. Mission

Mechanize the reviewed NQ/NASDAQ AM liquidity-reversal operation as an
independent QORE Trader candidate. This identity does not modify VT31 and does
not inherit any DEMO/LIVE authority from any existing Trader.

## 2. Market identity

- Canonical QORE market: `NAS100`.
- Current repository provider mapping: `NAS100 -> USTEC` on cTrader DEMO.
- USTEC CFD evidence is not exchange NQ futures evidence. The distinction must
  remain explicit in every artifact and result.
- V1 direction: LONG only, matching the reviewed source case.
- New York timezone is DST-aware.

## 3. Decision-time causal chain

V1 may become eligible only through information available at the decision time:

1. completed prior RTH session reference exists;
2. current RTH open at 09:30 New York is known;
3. an opening gap exists relative to the frozen prior RTH close;
4. price delivers lower from the RTH open toward a pre-existing sell-side
   reference;
5. the sell-side reference is swept;
6. the sweep occurs inside the frozen AM evaluation regime;
7. downside acceptance fails using only completed M1 bars;
8. bullish inversion-imbalance / reclaim evidence forms using only completed M1
   bars;
9. entry is taken only after that confirmation;
10. stop, target set and expiry are all known at entry.

No rule may use the final low of day, final session range, later MFE/MAE, later
target reach, or any other post-decision fact.

## 4. Frozen clock semantics

- RTH open anchor: 09:30 New York.
- Reviewed macro window: 10:50 inclusive through 11:10 exclusive New York.
- The exact V1 role of the macro window must be frozen before fresh holdout:
  validity gate vs contextual requirement may not be chosen after holdout.
- One completed-session opportunity maximum per New York trading date.

## 5. Mechanical primitives

The implementation must expose each primitive separately so it can be tested and
ablated without changing semantics:

- RTH prior close and current open;
- opening-gap size and signed direction;
- octant/quadrant coordinates of the opening gap;
- completed prior-session/day sell-side liquidity references;
- first causal sweep timestamp and depth;
- M1 close-based acceptance/rejection after the sweep;
- three-candle bullish FVG / inversion-FVG state;
- reclaim timestamp and valid entry envelope;
- structural invalidation under the swept extreme;
- pre-entry target ledger: relative/equal highs, wick CE where mechanically
  defined, and 09:30 open;
- lifecycle/expiry.

Source-language concepts that cannot be defined mechanically must fail closed;
they cannot be replaced by discretionary labels.

## 6. Development and ablation law

Only consumed NAS100 evidence may be used to debug or falsify mechanics before
the V1 freeze.

Mandatory explanatory ablations:
- FULL;
- NO_MACRO;
- NO_GAP_EXTENSION;
- NO_IFVG;
- NO_ACCEPTANCE_TEST;
- NO_RTH_GAP_CONTEXT.

Ablations are diagnostic. The fresh 1Y holdout evaluates only the preregistered
FULL identity. No ablation winner may be selected after opening fresh evidence.

## 7. Fresh holdout gate

Fresh historical evidence remains SEALED until:
- exact mechanics and numerical constants are frozen;
- source ambiguities are explicitly adjudicated;
- implementation and focused tests are green;
- static validation is green;
- friction/stress assumptions are frozen;
- candidate fingerprint is recorded;
- the repository-wide NAS100 consumption audit identifies a defensible untouched
  one-year interval;
- provider availability for the exact required M1 evidence is established
  without inspecting economic outcomes.

The holdout is opened once. After opening it is permanently consumed.

## 8. Required result metrics

- eligible sessions and opportunity funnel;
- setups, trades and no-trades;
- win/loss/breakeven;
- gross R and friction-adjusted R;
- PF and expectancy;
- max drawdown R;
- max losing streak;
- false-bottom rate;
- MAE/MFE and time-to-event;
- target attribution;
- monthly and quarterly stability;
- stress-friction result;
- deterministic same-bar collision policy;
- bootstrap/resampling uncertainty;
- evidence fingerprints and exact git SHA.

## 9. Governance

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`REAL_CAPITAL_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`

No merge without explicit Owner order.
