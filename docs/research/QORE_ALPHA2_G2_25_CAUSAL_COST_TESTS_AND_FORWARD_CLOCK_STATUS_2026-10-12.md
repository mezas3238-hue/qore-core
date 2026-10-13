# QORE-Alpha 2 — G2 CAUSAL ECONOMICS implementation certificate, synthetic only

**2026-10-12.** Preregistered before code: `docs/research/QORE_ALPHA2_G2_CAUSAL_ECONOMICS_STRESS_ENGINE_PREREG_2026-10-12.md` commit `fff976831ea68502f85322d76e73ebea96d19e2f`. Research HEAD tested `64c301894f4c28cb1d1aeac0332cb9c10130ff34`. [GitHub Actions #38293812287](https://github.com/mezas3238-hue/qore-core/actions/runs/38293812287) final **SUCCESS** with Ruff PASS + **25/25 pytest**. No broker authentication or source real prices consumed in these tests. All inputs 100% synthetic and user market methodology W1/W2/W3 unchanged.

## Executable research-only economic contract

`src/qore/research/alpha2_g2_causal_economic_stress.py` requires `QuoteObservation` records on both entry and exit with independent exact account/symbol and `available_at <= decision_at`; each quote <= 5 seconds old, positive spread. No source claim can be upgraded from historically downloaded event-time to first-delivery time without prospective proof.

It additionally requires exact broker contract with instrument ID (no NAS100/USTEC inferred equivalence), positive trade units, positive **cash in quote currency per trade unit per unit of price move**, valid-at-decision linear payoff and fees with separate original SHA witnesses and a source-known effective interval. Exit quote-currency to deposit-currency conversion must be a finite Decimal and first-known by exit; for foreign currency, the conversion rate cannot be more than 5 seconds old. Same-currency conversion must be exactly unity.

`ExplicitCostWitness` requires **six explicitly provided finite Decimal fields**: commission entry, commission exit, funding, swap, adverse slippage entry price, adverse slippage exit price. No defaults. Zero is allowed ONLY as an explicit signed source value; absent value fails closed. Positive cash risk denominator required. Since the raw side quotations are **references**, adverse slippage is subtracted from projected quote prices. Broker DEAL executions are NOT used here, so no actual fills or NET proof is claimed and no double counting of broker fill slippage is allowed.

### Exact synthetic arithmetic test for deterministic reproducibility (NOT ACTUAL ALPHA2)

Long example: entry BID 100 / ASK 101, exit BID 103 / ASK 104, exposure 10 quote cash units per price unit, identity conversion, entry adverse slip 0.1 price unit, exit slip 0.2, commissions 1 and 2 deposit, funding 0.1 and swap 0.5. Reference gross 20 deposit; stressed gross 17; all fees 3.6; hypothetical remainder 13.4; hypothetical R=0.134 for assumed synthetic risk cash 100. No historical prices or trading strategy used. Short sign/sides also tested.

Other tests reject: source future and stale events; wrong account; false alias; bid=ask; non-finite money; float/bool as monetary evidence; missing fee field; evidence SHA absent; contract fee expired; conversion after exit; stale FX conversion; non-linear payoff; zero risk; negative order price after stress. Output status **HYPOTHETICAL_QUOTE_COST_STRESS_NOT_NET_CERTIFICATION**, `broker_actual_net_attested=false`, `utc001_certified=false`.

**The conditions for Alpha2 certification are STILL UNMET:** sampled 29-market 2020+2023 historical quotes cannot pass current-source first receipt, do not cover actual entry/exit histories; 12 vs21 original broker contract/account comparability unresolved; fees, swap, slippage and PIT news are unavailable for all orders, no virgin OOS. W1, W2, W3 gross NO_SUPPORT unchanged. No capital/PAPER/VPS/MT5/Shared/CIBO/QDLE trades authorized.

## Separate new forward observer

Prereg `docs/research/QORE_ALPHA2_G2_NZDUSD_DEMO_FORWARD_RECEIPT_45S_PREREG_2026-10-12.md` commit `14f7b54ed5e1ffd1c179faf500fa8646837a6da9`; source-only cTrader DEMO NZDUSD 45s workflow [#38294483765](https://github.com/mezas3238-hue/qore-core/actions/runs/38294483765). Any runner status pending/in_progress without final signed source manifest is **NOT proof** quotes were captured. Collector read-time is first-observed by runner, not actual broker matching engine arrival time, and historical available_at remains unverified. Keep status blocked if no independently verified artifact.
