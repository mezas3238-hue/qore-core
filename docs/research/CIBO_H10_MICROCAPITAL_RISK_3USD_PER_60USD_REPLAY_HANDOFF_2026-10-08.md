# QORE CIBO — H10 CORRECTED: USD60 -> USD3 STOP RISK (5%) | OCT 08, 2026

**OWNED MICROCAPITAL POLICY** — The owner explicitly corrected the risk premise. The old H10 0.25% ($0.15 at $60) is **REJECTED AND SUPERSEDED**. User demand: at $60, risk **at least $3 at the stop** when the position is actually executable. This is **5% of $60**, not a funded-account rule. **Fees are charged separately**: at user model 7 USD/lot open + 7 USD/lot close, 0.03 lot pays $0.42 total; losing $3 at stop costs $3.42 before spread/slippage. Never hide the fee in the stop-dollar figure or confuse it with free headroom.

## Branch and code

Independent branch `agent/cibo-microcapital-compound-risk-h10-001`; script `src/qore/infrastructure/trader_lab/cibo_microcapital_sizing_h10.py`, corrected source commit `0e6029fb8e43cdb54a4002313f9261ac1534f07e`; 9 new isolated unit tests in `tests/trader_lab/test_cibo_microcapital_sizing_h10.py`, commit `8ff70a0b6cd25e419f01bc36301bfbb5a11b7782`.

The causal target is `min(balance*0.05, 3 + 0.008*max(balance-60,0))` dollars **of stop exposure** before fee, scaled down when already in drawdown. At a healthy $60 account target=$3; $100->$3.32; $500->$6.52; $2,000->$18.52. This is gentle *USD* escalation, not 5% on every larger balance. It is a **target, not a guaranteed fill**; broker volume increments may make exact $3 impossible. This is an experimental capital allocation schedule, not machine learning or certified profitability.

Two distinct account types:
- `micro_research`: hypothetical $60/$100/$500 seed, NOT FundedNext Stellar Instant. Example risk control max **10% of current equity** in aggregate and 10% session budget; trailing floor in local research model ~25% of balance high (parameterized). Tighten when DD worsens.
- `stellar_instant`: REALISTIC USD2k rule research. User-imposed $60 internal daily cap and funder 6% trailing max-loss + 3% total instantaneous exposure. **The micro 5% rule can never override these caps.** Risk target at healthy 2k $18.52 stop, fee extra, with all-in headroom and concurrent $60 cap; do not confuse with a mandatory $60 risk per trade.

Never block/reject/rewrite Trader entries to fabricate profitability; an unfundable executed entry makes the scientific run **invalid**, with explicit risk, margin and lot diagnostics. This is important because an execution-first architecture with no broker finance cannot physically honor all 3,368 original entries at $60. Historical 3,368 recorded remains the audit denominator.

## Locally executed chronological 3,368-source replay after risk correction (H10 draft simulator)

**9 complete attempted chronological cases, all halted at first infeasible entry (FAIL CLOSED).** 2019–22 historical source; broker-provider snapshot is 2026 and margin/FX conversions estimated; no intratrade MTM or spread tick custody, not official FundedNext proof.

| Starting equity | Extra adverse slippage | Entries financed before first failure | Terminal balance **at halted attempt** | Cause |
|---:|---:|---:|---:|---|
| $60 | 0R | **0** | $60 | Historical NAS100 min 0.10 lot needed ~$77.79 estimated margin |
| $60 | 0.25R | 0 | $60 | Same margin incompatibility |
| $100 | 0R | **12** | $94.18 | Minimum required risk/remaining daily exposure |
| $100 | 0.25R | 5 | $96.23 | Minimum required risk/remaining daily exposure |
| $500 | 0R | **22** | $467.03 | Minimum required risk/remaining daily exposure |
| $500 | 0.25R | 22 | $465.80 | Minimum required risk/remaining daily exposure |
| $2,000 | 0R | **51** | $1,880.36 | Minimum required risk/remaining funded headroom |
| $2,000 | 0.25R | 29 | $1,884.25 | Minimum required risk/remaining funded headroom |

Additional old fixed-$10 comparison of 2k: **16** entries, halted at $1,881.11 — NOT a promotional carrier.

The $60 first-trade margin result is a hard incompatibility **under the historical broker minimum-volume and estimated margin model**. It is not proof the actual current NAS100 contract has precisely that requirement; need actual real broker specs. Never silently force 0.001 lot if real symbol min is 0.1. Under synthetically **executable** micro-volume settings with $60 and 0.03 lot, stop-dollar target **$3** and user commission **$0.42**, the toy account settled a -1R loss at **$56.58** (3+0.42). This is only a unit-level demonstration, NOT live/profitability validation.

**Local regression:** 8/8 synthetics PASS: 3 stop at $60, gradual balance scaling, drawdown taper, double-leg per-lot fee, physical micro-volume, impossible minlot no fabricated fill, no future R sizing leakage, USD6 sample micro daily risk gate. GitHub 9 pure planner tests are published but their CI result is not claimed.

**Next scientific work:** secure *genuine* microcontract symbol min volumes, tick value, leverage and margin; determine whether a real USD60 start can support the required original signal corpus. First certify financing under chosen broker. Then integrate CIBO's full four capital motors and micro-sizing into exact Trader Lab, run cold/warm reproducible 3y replay, validate full 3,368 custody, fees, MLL and floating equity, and audit all losing clusters. If source signals require more capital than exists, label the architecture incompatible rather than counting nonexistent gains. Full scientific certification pending.

**Key priority:** protect survival and gradual compounding with **user $3 risk per $60 stop objective**, no return guarantee and no premature approval of micro/funded trading.
