# VT08 Forex Cognitive V1 — Market Memory / Trader Experience Binding

Status: **CONSUMED-EVIDENCE MEMORY FOUNDATION / PARALLEL RESEARCH-SHADOW / NOT LIVE-WIRED**

This checkpoint binds Cognitive V1 to the exact VT08 R3.15 independent-validation evidence without turning historical PnL into runtime rules.

## Evidence source

GitHub Actions run: `34759027136`  
Evidence HEAD: `64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222`  
Holdout: `VT08_R3_15_FINAL_INDEPENDENT_2020_2022`  
Window: `[2020-07-01, 2022-07-01)`

Exact market artifacts are bound in `vt08_cognitive_cibo_market_memory.py` by artifact ID and SHA-256 digest.

## CIBO Market Memory

For each authorized VT08 Forex market and Owner anchor 01/05/09 New York, the memory retains aggregate structural priors derived from complete four-hour windows reconstructed from closed M15 evidence:

- H4 range distribution in basis points;
- median body fraction;
- median close location;
- median upper/lower wick fraction;
- historical bullish-close rate.

These are **association-only priors**. They cannot select a market, side, anchor, setup, or order.

## Trader Experience Memory

The same consumed window is decomposed by `Market × Anchor` for the B01 methodology interaction:

- sample;
- wins/losses;
- mean return;
- PF;
- side counts;
- terminal-path counts (stop / target / H4 containment).

These outcome fields exist to retain Trader experience and guide future causal research. **PF or PnL is explicitly forbidden as a direct EXECUTE/WAIT/ABSTAIN gate.**

R3.15 certification authority remains separate:

- AUDJPY: SHORT;
- GBPJPY: LONG + SHORT;
- GBPUSD: SHORT.

Memory presence for AUDUSD/EURUSD/USDCAD/USDJPY grants no certification or execution authority.

## Market × Anchor principle

Cognitive V1 now has independent cells for all:

`{AUDJPY,AUDUSD,EURUSD,GBPJPY,GBPUSD,USDCAD,USDJPY} × {01,05,09 NY}`

The cells are not assumed interchangeable. However, historical differences are not promoted into rules until a decision-time causal mechanism is identified and validated.

## Governance

- no methodology mutation;
- no retrospective best-market/best-anchor selection;
- no date-level outcome oracle;
- no future-bar runtime lookup;
- no runtime PnL self-training;
- no cross-trader knowledge import;
- CIBO Market Memory cannot issue execution authority;
- Trader Experience Memory cannot issue execution authority;
- QORE Risk remains final capital authority;
- current operational VT08 remains untouched.
