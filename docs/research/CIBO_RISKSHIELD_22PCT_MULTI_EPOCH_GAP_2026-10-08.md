# CIBO RiskShield — 22% multi-epoch engineering gap and continuity

**Date:** 2026-10-08. **Status:** research-only, reused holdout. **Canonical 37.772111615% source:** [run 37716702999](https://github.com/mezas3238-hue/qore-core/actions/runs/37716702999), artifact 11523494908, `carrier37772-p4150.json`. **Owner lane:** isolated branch `agent/cibo-riskshield-portfolio-shock-e1-001`. No production or canonical policy promotion.

## Frozen baseline
- Initial capital: USD 60.
- Terminal capital: **USD 668,910.439682713**. Frozen economic **minimum** USD 582,440.025295; preferred competitive benchmark is USD 668,910.43968 or more.
- Max observed historical DD **37.7721116155%**; goal **22% or lower** as a replay-verified DD milestone (distinct from final certification).
- Total gross loss **USD 957,225.911831171**; ATTACK gross loss **USD 955,665.772155971**. 3,368/3,368 entries (860 ATTACK + 2,508 MEDIUM).
- `attack_sovereign_breach_usd=0`. **Separate accounting caveat:** `sovereign_floor_breach_usd=84.617235934...` in this artifact; it must be investigated independently before any certification or blanket “zero sovereign breach” claim. These fields are not interchangeable.

## Top-ten drawdown headroom gap

The below estimate applies **only if each episode's peak capital were unchanged**, which is NOT true under an altered policy; it is a forensic scale-of-problem proxy, not a causal prediction or an attainable profit promise.

| Rank | Peak date | Mode driver | Current DD | Original peak USD | Original loss USD | Reduction to 22% at same peak |
|---|---|---|---:|---:|---:|---:|
| 1 | 2021-02-09 | ATTACK | 37.7721% | 61,696.54 | 23,304.09 | 9,730.85 |
| 2 | 2019-07-19 | MEDIUM | 37.6660% | 79.76 | 30.04 | 12.50 |
| 3 | 2020-09-10 | ATTACK | 37.0168% | 12,867.91 | 4,763.29 | 1,932.35 |
| 4 | 2020-04-03 | ATTACK | 36.4063% | 703.85 | 256.25 | 101.40 |
| 5 | 2020-01-31 | mixed | 34.8693% | 114.11 | 39.79 | 14.69 |
| 6 | 2020-03-23 | ATTACK | 32.3447% | 566.09 | 183.10 | 58.56 |
| 7 | 2019-11-04 | mixed | 31.5321% | 95.65 | 30.16 | 9.12 |
| 8 | 2020-08-19 | ATTACK | 31.3885% | 11,794.59 | 3,702.14 | 1,107.33 |
| 9 | 2020-05-21 | ATTACK | 30.7466% | 1,203.98 | 370.18 | 105.31 |
| 10 | 2020-06-24 | ATTACK | 30.0799% | 4,143.98 | 1,246.51 | 334.83 |

Source: `drawdown_forensics.top_10_episodes` from the exact frozen control artifact above. Instrumentation and values are from **observed replay**, not invented holdout outcomes.

## Causal scientific takeaway

An ATTACK-only reduction in 2021 cannot yield <=22% multi-year max DD: the original top 10 episodes all exceed 30%, including early low-capital MEDIUM. The system needs an additive **portfolio-level forward-looking stress headroom monitor** coordinated with MEDIUM position lifecycle *and* ATTACK risk allocation, with positive-expected-growth differentiation, rather than arbitrary multiplier-wide tapers.

The 22% design objective must check **top 10 DD episode drawdowns**, not only the worst, after every accepted replay. An apparent 37.77 → 37.66 move merely migrates to 2019 and is not close to 22-ready. Frozen win/loss conservation, terminal wealth and trading authority are simultaneous objectives.

### Priority action sequence

1. E1 [portfolio shock trial](https://github.com/mezas3238-hue/qore-core/actions/runs/37721188855) modifies only past-ATTACK-loss trigger and taper on an isolated branch while retaining all 7 windows; compare baseline and 8 candidates for activation counts, capital, DD and gross loss.
2. If broad shock sweeps fail (likely due path dependence), **stop blind tuning**. Implement deterministic causal stress-headroom diagnostics with current portfolio peak, equity, existing open stop risk, correlated cross-symbol exposures and cost/slippage stress. A fully blind guaranteed DD threshold is not possible.
3. Stage an optional post-entry **RiskShield manager** (conditional partial exit/stop management, respecting Trader authority) and evaluate its incremental benefit against no intervention. No outcomes known at decision time; no no-entry authority for CIBO.
4. Track whether the proposal damaged winners, not merely reduced gross loss. The goal is at least the sovereign frozen floor, and preferably >= USD 668,910.44 capital, while compressing DD and losses.
5. Preserve the independent fresh three-year holdout sealed. Repeated research tuning is never certification.

**“Trabajo cumplido” must be reserved strictly for a completed reproducible <=22% max-DD replay with >= USD 582,440.03 capital, all 3,368 entries, 0 ATTACK sovereign breaches, no source/lookahead leakage and losses constrained under current governance; separately flag any remaining accounting sovereignty anomalies.**
