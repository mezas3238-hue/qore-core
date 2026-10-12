# QORE Native G1 — frozen source-only cross-asset tick pilot (2026-10-12)

This preregistration is independent of prior 231 strategy PnL tests. The question is **availability of original historical BID and ASK**, not alpha. Prior validated NZDUSD source: run 38279593236, source artifact 11760547215.

Frozen target 1: canonical **XAGUSD**, provider exact XAGUSD (metal).
Frozen target 2: canonical **SP500**, provider exact **US500** (index), historical mapping only; current symbol ID must be positively confirmed on the same authorized IC Markets DEMO account. Neither is selected by market returns.

Both instruments use the same three **ten-minute UTC windows** already frozen for NZDUSD:
- 2020-09-15T13:00:00Z to 2020-09-15T13:10:00Z
- 2023-09-19T13:00:00Z to 2023-09-19T13:10:00Z
- 2026-09-15T13:00:00Z to 2026-09-15T13:10:00Z

Acquire by official read-only cTrader Open API ProtoOAGetTickDataReq on BID and ASK, 12 minimum side requests. Complete hasMore by disjoint splits; native newest-first requires first absolute timestamp AND integer price then signed time AND price delta accumulation. Save original reconstructed integer and Decimal decoded side files with independent SHA256. No M1/M5 tick synthesis or OHLC return access. Fail closed on absent side, unauthorized broker, source identity or provider response. Zero/negative spreads never represent free fills.

Publish source files only as expiring private-access GitHub Actions artifacts, **not raw price commits** to this public repository. Two jobs run sequentially. Frozen windows may not be changed after results. Strictly no economic strategy results, no order placement, no token refresh, no production deployment. Success only proves source access for the checked windows, never complete 33 market history, executable costs or certification.

Follow-up: independently audit all file SHA256, UTC chronology, tick decimals, as-of quality and timestamps; then evaluate feasible longer source coverage before net trading tests. Traders certified 0/3 and native historical NET blocked.
