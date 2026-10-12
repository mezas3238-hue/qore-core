# QORE-Alpha 2 G2 / issue #868 — offline original evidence exact33 contract census, prereg

**Date** 2026-10-12. **PR** #840 DRAFT. **Scope** six *already existing* GitHub Actions source/QA runs; only repository metadata and a fixed original33 roster. This is **NOT** a new broker observation, order, PnL, strategy improvement, economic certification or privileged vault access. Original source outcomes already disclosed, so this is a reproducibility/lineage engineering gate, NOT a fresh hypothesis or holdout.

## Invariant

Original G0 M5 roster is 33 symbols, **Atlas Original12** + **ICMarkets New21**, and those must NEVER silently become the same broker account/product. G0 manifest hash `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`. Exact 29 demo spot pilot covers `MARKETS - {NAS100,SP500,NZDUSD,XAGUSD}`; NZDUSD has a **separate** 45-second spot capture; USTEC catalog is an alias candidate to NAS100 **only**, not a historical NAS100 contract. SP500→US500 remains an *unproven alias*, XAGUSD only earlier short archived windows reported by separate G1; no new prospective Alpha2 source admitted for them.

## Frozen immutable GitHub API metadata anchors (GET only)

All six run IDs / exact code head SHA / artifact ID / artifact ZIP digest below are independently visible through GitHub API today, not price bytes.

| Identity | Run | Exact HEAD | Artifact ID | ZIP sha256 |
|---|---:|---|---:|---|
| DEMO_EXACT29_SOURCE | 38298399112 | 33068c720fedb3d358a2f73e7323508abd8365f6 | 11769446263 | 6de061c63d570e2c004fd4192b3771395fd33ba68199df620447046baf081472 |
| DEMO_EXACT29_INDEPENDENT_QA | 38298920851 | a80702b40e2242f7da05d392137cc76ce7124b8b | 11770276257 | 0787fa156e5a4d5b885d27ff8aee8ce831618ae5fd1cee16eb742294ba2a6bb6 |
| DEMO_NZDUSD_SOURCE | 38296610948 | ca32ad2311c5c6b4a9312073ca0b4c7b53109a75 | 11767978684 | f3e0e8e52f459e8c2ec136a84b4346dd81f130787fe0430b0ed4bc7b9c4e9039 |
| DEMO_NZDUSD_INDEPENDENT_QA | 38297614422 | 2c39e6e5c4047f2c30ffdcf84c271ead07aa8167 | 11768424790 | b6ed9e8ae23fd17be7c9fcfd93c386f6309303154631177e8d924cefd829f0cf |
| DEMO_USTEC_CATALOG_SOURCE | 38284304699 | 716996e0f893af0aeb2b990ac11d644cf62a5c5f | 11762018327 | 7f927792e575c5cccb9932c55a8db6733430c34629681701c6acd98491ac5c2e |
| DEMO_USTEC_INDEPENDENT_QA | 38301861733 | b163b37f5681abfae5cfb6a0a38890c7db14506b | 11771250981 | ed60441604a5878d5aca7bcb4c710aba7f229d2a54b384c423fc3490ab071a0f |

## Exact audit acceptance, no substitutions

1. Fetch only the six GitHub REST /actions/runs/{runid} and /actions/runs/{runid}/artifacts API **metadata** from authenticated GitHub Actions with read-only token. Require exact six run IDs, code heads, `completed/success`, `run_attempt=1`; exactly one original artifact per run, exact frozen ID/name prefix and `digest=sha256:<64hex>`, `expired=false`, `size_in_bytes>0`. Do not download artifact ZIPs or quotes.
2. Enumerate 33 original symbols exactly, keep Atlas12/New21 source cohort distinguishable; exact29 set derived from existing original source module, not manual range. Every row must make `historical_original_account_contract_equivalent=false`, `contract_fee_schedule_verified=false`, `net_eligible=false`, `UTC001_certified=false`; never fill missing cash/point, swaps, commissions, minimum fees, sessions, validity, account scope with synthetic zeros. Asset identity cannot be presumed solely from its ticker.
3. For 29 symbols label `29_EXACT_DEMO_60S_SOURCE_SHA_WITNESS_ONLY` (not fills). NZDUSD `SEPARATE_DEMO_45S_SOURCE_SHA_WITNESS_ONLY`. NAS100 `USTEC_CATALOG_ALIAS_METADATA_SHA_ONLY_NOT_EQUIVALENT`; SP500 `US500_REPORTED_HISTORICAL_ALIAS_NOT_CONTRACT_QA`; XAGUSD `HISTORICAL_SHORT_WINDOWS_REPORTED_NO_PROSPECTIVE_EXACT_QA`. All 33 remain contract blocked. The last two labels are *document references*, NOT observed by the six-run audit.
4. Source-level claim must be limited to **GitHub API metadata lineage verified**, NOT artifact byte contents independently rehashed in this run, not historical market execution availability, not original Atlas account economy and not 33 simultaneous first-receipt.
5. Any missing, failed, mutated, expired artifact or wrong-head GitHub run => fail closed; no generated positive report. Synthetic tests must poison alias, source SHA, alternate run/attempt, original cohort and missing symbol, and all claims of NET/UTC001.
6. Output a human-readable blocked census and machine-readable JSON with 33 rows and six evidence heads/IDs/SHA, no account secret, no price values, no order fields; source witness time and execution status must be explicit.
7. No new broker SymbolById request after V1/V2/V3 failure; no historical 2026 reserved window read; no strategy retuning or W4 mining. Stay DRAFT/NO MAIN/NO VPS/NO MT5/NO CIBO/NO Shared/NO orders.

## Owner gates not satisfied by this delivery

Historical original12 account/contract point payout, unit specifications, symbolId validity, Atlas⇔ICMarkets equivalence, economic fees/swap/financing, true BID/ASK decision+exit available-at, NEWS-PIT and fresh OOS still pending (#852/#868). 33-signal universe source ≠ broker execution permit. Data archival legality and vault restore remain #837, separately pending. Research W1/W2/W3 gross = NO_SUPPORT and frozen; **zero candidate certified**.
