# QORE Native G1-PRE — 29-market native BID/ASK availability census (FROZEN 2026-10-12)

**Priority SOURCE, not strategies.** Before these requests, 3 symbols are already captured with 3×10min original cTrader BID/ASK: NZDUSD, XAGUSD, canonical SP500→provider US500. Source runs #38279593236 and #38282585181; independent SHA/as-of QA runs #38280521951 and #38283148986. Original G0 33 M5 provenance SHA 1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85. No strategy net certification.

**Source catalog precedent:** successful IC Markets cTrader DEMO source catalog artifact #11753132568, run #38262534602: 32 enabled *provider names* including US500 (SP500 documented alias), 29 other exact QORE instrument names and NZDUSD/XAGUSD. NAS100 neither exact available nor USTEC independently verified in this catalog; **exclude NAS100**, not infer an alias.

## Frozen targets before any source request

Reuse canonical group universe of exactly 33 in `qore_native_universe_33_source_registry_v1.universe`. Exclude already captured `NZDUSD, XAGUSD, SP500`, and unresolved alias `NAS100`, producing **29 remaining distinct symbols**, all requiring exact broker symbol name and positive `symbolId`. No extra discovery based on PnL. Do not redownload previous 3. Use **exact same three windows** for *each* of 29 markets (all UTC):
- 2020-09-15T13:00Z—13:10Z
- 2023-09-19T13:00Z—13:10Z
- 2026-09-15T13:00Z—13:10Z

Thus 29×3×2=**174 minimal BID/ASK requests** and more only for `hasMore`. A continuous 10-year BID/ASK archive is not claimed. The 2026 window is source availability testing only, **not opened economic holdout**. The source catalog's 32 symbol availability does not prove even one native tick request until run completes.

## Execution

One bounded read-only official Spotware cTrader DEMO session after independent `probe_catalog()` broker-and-account proof. Only six native side requests per symbol using `ProtoOAGetTickDataReq`, shortest 10-minute windows; 0.30s minimum API pacing, `hasMore` fail-closed millisecond pagination (<=64 requests per side/window), original signed time and signed price deltas from official Open API, integer prices + decimal normalized records and individual SHA256 hashes. Separate per-market source directory and failure witness, so an unavailable symbol does not abort other source checks. No server-side source deletion, no account orders, no OAuth refresh and no user secrets written to artifacts. One job to avoid 29 duplicate OAuth handshakes and prevent parallel rate-limit pressure.

Each symbol SOURCE_PASS only if all six BID/ASK sides nonempty and hash ledgers published. Overall PASS only if exactly 29 SOURCE_PASS; otherwise PARTIAL with per-market sanitized blocker (not proof market lacks quotes). This census is deliberately independent of seven methodology returns, Holm/FDR/E3, and the CIBO Ultra Fast strategy result-cache. It does not make any claim about full historical 33-market coverage, historical fee/contract equivalence, fills, net PnL, Sharpe, Sortino, PF, DD or CIBO/Shared/Trader certification. No VPS, MT5, LIVE, Shared, QDLE or CIBO changes.

**Follow-up P0**: retrieve artifact and independently inspect SHA, chronology, 5s as-of spread cross/zero/stale and alias provenance by symbol; cure NAS100 exact provider symbol ID separately. Then plan bounded longer archival windows with cost, contract and news point-in-time gates before economic backtests. Archive source artifacts privately with licensing check before GitHub Actions 90d retention ends, under #837; never write raw broker price dumps as a Git commit in public repository.
