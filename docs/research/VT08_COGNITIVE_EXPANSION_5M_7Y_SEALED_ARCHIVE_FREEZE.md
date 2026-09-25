# VT08 Cognitive Expansion — Five-Market 7Y Sealed Archive Freeze

Status: **RAW COLLECTION ONLY / NO STRATEGY REPLAY**

The five expansion markets are frozen:
EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD.

The archive requests 2,555 calendar days of read-only cTrader DEMO history.
Base evidence contains M5/M15/H4; M3 is collected independently on the exact
same requested/checked boundaries.

The archive is sealed before any new candidate is tested against the older
window. No strategy replay, trade construction, PnL, PF, DD or candidate
selection may run during collection.

For future validation, evidence at or after
2023-09-24T23:45:00Z is treated as consumed. A fresh replay must use signals
and exits strictly before that cutoff.

research_only=true
sealed_raw_archive=true
strategy_replay_performed=false
live_authorized=false
