# QORE-Alpha 2 — G2 29 simultaneous IC Markets DEMO source, 1,033 spot events, independent QA

**2026-10-12.** Authenticated exact canonical-source **29 DEMO instruments** in one cTrader Open API spot subscription (no trades, no refresh). Two PRE-registered source experiments and independent signed artifacts with NO economic trading claims.

## Exact proof chain

- 29-market first receipt SOURCE prereg in `docs/research/QORE_ALPHA2_G2_29_EXACT_DEMO_MULTISPOT_60S_PREREG_2026-10-12.md`, Git ancestor `34a2c20d285d86a16c95bac217a0dc9225a6d799` **before collector outcomes**. Source worker `src/qore/research/alpha2_g2_29_exact_demo_forward_multispot.py`, synthetic unit tests `tests/research/test_alpha2_g2_29_exact_demo_forward_multispot.py`.
- Original first-receipt DEMO capture [GitHub Actions #38298399112](https://github.com/mezas3238-hue/qore-core/actions/runs/38298399112) **SUCCESS 2/2 jobs**; exact HEAD `33068c720fedb3d358a2f73e7323508abd8365f6`, artifact #11769446263. Exactly 29 exact G0 canonical symbols sourced from original SOURCE29, no NAS100/USTEC or SP500/US500 aliases inferred. One `ProtoOASubscribeSpotsReq` with repeated 29 IDs, provider timestamp requested, bounded 60sec after ACK. Source log **1.033 events**, **29/29 markets had BID and ASK updates**, 0 orders, no token refresh, no broker account ID persisted. First attempt run #38298284942 failed Ruff PRE-SOURCE, import ordering fixed before contacting broker.
- Independent QA PRE-registered in `docs/research/QORE_ALPHA2_G2_29_FORWARD_SOURCE_INDEPENDENT_SHA_QA_PREREG_2026-10-12.md`, commit `09c01e6d4c3b05844b7d1638d760efb4bab9fcf4` (frozen before original outcome publication). Original 29 per-market files+manifest SHA both verified against SHA ledgers; independent global sequence, per-market sequence, UTC first received and provider timestamp, reconstructed each bid/ask 5sec side freshness.
- Independent [GitHub Actions #38298920851](https://github.com/mezas3238-hue/qore-core/actions/runs/38298920851) **SUCCESS**, Ruff and **7/7** synthetic defensive tests; exact auditor HEAD `a80702b40e2242f7da05d392137cc76ce7124b8b`, signed independent artifact #11770276257. Outcome `G2_29_DEMO_FIRSTRECEIPT_ORIGINAL_SHA_AND_SIDE_QA_PASS_NOT_NET`. Audit rechecked 1.033 original events, all 29 BID and ASK:

| Independently reconstructed first-seen source state | Events |
|---|---:|
| Fresh, strictly positive ASK>BID, SOURCE-ONLY | **890** |
| BID or ASK absent / last seen older than 5s | **107** |
| Fresh ASK=BID, QUARANTINED NO FREE FILL | **36** |
| Fresh ASK<BID, CROSSED QUARANTINED | **0** |
| **TOTAL** | **1.033** |

The 890 source events with 2 positive quote sides are NOT 890 tradable signals or verified fills; multiple events can update a single side while reusing the other, and source timestamps refer to app dequeuing after event reception, not broker execution availability. No actual NET, swap, commissions, fills, slippage, PIT news or risk/UTC001 inference. Original 29/29 status does not prove 24/7 market continuity, historical bidask availability for 2016–2024, or certified broker account identity matching the Atlas Original12. No PnL processed.

## Remaining 4 sources and next technical gates

Fixed excluded canonical names `NAS100`, `NZDUSD`, `SP500`, `XAGUSD`. NZDUSD is separately captured [single-symbol run #38296610948](https://github.com/mezas3238-hue/qore-core/actions/runs/38296610948), 11 real events and independent QA #38297614422; XAGUSD and SP500/US500 historical SOURCE pilots have independent original QORE Native evidence; NAS100/USTEC is an alias candidate, **NOT contract equivalence**. Therefore 29 simultaneous exact plus 1 independently captured symbol demonstrates 30 names with some current receipt data but **NOT a single unified 30-account simultaneous proof** nor all 33 and not a contract certificate.

Before any expansion to 33 or economic replay: freeze read-only original broker symbol contract IDs/pip digits/point value/lot step/instrument schedule and exact account cohort equivalence, separate alias proofs (NAS100 vs USTEC; SP500 vs US500). Source event receiver must archive actual first-received timestamps and both side ages for long enough to cover independently preregistered entry AND exit; versioned retention, source SHA and cost/PIT fee books. Existing W3 24.487 original opportunities have only 2 entries and ZERO full exits overlapped by historic 29 x2 ten-minute snapshot windows [#38297579449](https://github.com/mezas3238-hue/qore-core/actions/runs/38297579449). Frozen W1/W2/W3 remain gross NO_SUPPORT; do not tune them.

**0 real/PAPER/DEMO orders, 0 trader Alpha2 certified, NO VPS/MT5/Shared/CIBO/QDLE/production modifications.** PR #840 DRAFT, original issue #852 OPEN.
