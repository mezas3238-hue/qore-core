# QORE Native G1-PRE NAS100/USTEC provider alias feasibility — PREREG 2026-10-12

This is a **source-catalog-only** experiment, not a historical strategy test. Original G0 archived NAS100 (12 original CIBO M5) has the documented historical provider alias hint `USTEC` (`CANONICAL_ALIAS_HINTS` in QORE frozen 33 universe registry); however the current IC Markets DEMO catalog preflight found no exact `NAS100` symbol. The absence of exact NAS100 does NOT prove the broker lacks a U.S. technology 100 instrument. It DOES prohibit silently mapping unknown CFD contracts based on price similarity.

## Frozen before lookup

Query the **already verified IC Markets DEMO account** by the official read-only `ProtoOASymbolsListReq` and accept exactly:
1. Exact canonical `NAS100` enabled, or
2. Single provider symbol named **`USTEC`** enabled as **UNVERIFIED_ALIAS_CANDIDATE**.

No other alias names may be selected. If both are enabled, record both and **do not automatically choose** without contract adjudication; if repeated/ambiguous, fail closed. Use provider-assigned positive `symbolId` and `ProtoOASymbolByIdReq` for native metadata *only*. Do not use price similarity, backtest PnL, screenshot NDX100, or outcome-based remapping.

No `ProtoOAGetTickDataReq` in this stage; no raw BID/ASK data download, no orders, no OAuth refresh, no account IDs or tokens in logs/artifacts. The result can only be `EXACT_NAS100_ENABLED`, `USTEC_ALIAS_CANDIDATE_NEEDS_CONTRACT_EQUIVALENCE`, `BOTH_AMBIGUOUS`, or `NOT_LISTED/UNAVAILABLE`.

Even if USTEC exists, original CIBO NAS100 contract vs IC Markets DEMO USTEC contract, point value/CFD lot sizes, trading hours, min tick and currency exposure remain **unproven**, and NAS100 stays blocked from any NET backtest. This check is independent from the 29 existing exact-symbol source census. Holdout never opened. Source-only research GitHub, no production/VPS/MT5/LIVE/CIBO/Shared/QDLE.
