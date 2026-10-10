# QORE CORE CIBO — Four-arm original 3368-source PAPER book integration

**Estado:** P0 research-stage contract; **NOT the financial replay**. Date 2026-10-09. Integrator PR #745.

## Functionality now physically implemented

`scripts/cibo_p0_four_arm_native_paper_orchestrator.py` joins:
- Original 2019–22 signed/artifact SHA-verifiable seven-Trader `walk-forward-manifest.json` (3368 unique fingerprints);
- frozen A-X / A-Y / B-X / B-Y counterfactual policy contract;
- **one canonical `PaperQDLE` SQLite file per arm**, each containing its own `CanonicalPaperPortfolioMtm` cash/equity account inside that same SQLite;
- chronological source traversal with `PAPER_UNASSESSABLE_NO_PHYSICAL_QUOTE` receipts for signals lacking broker-attested native data and four contemporaneous Native MAX/motor votes;
- WAL-safe SQLite backups with SHA256, per-arm JSON receipts and exact source conservation assertions.

The four books remain independent even before trades: `meta.canonical_paper_scenario_arm` stores immutable arm identity and `PAPER_SCENARIO_ARM_BOUND` is journaled. **Require four distinct audit digest/SQLite hashes** to prevent mislabeled account replay artifacts.

**Paper executor bridge exposed**: `ArmBook.mark_and_publish`, `reserve`, `filled`, `settled`. Their underlying implementation is the same live-forbidden QDLE and MTM ledger; new financing can occur only after a fresh full-market BID/ASK mark from the same SQLite. A `NoNativeBrokerCalculator` explicitly refuses invented physical lots until an independently validated historical broker calculator is supplied. This implementation **does not construct fictitious live deals, independent fee evidence, market quotes or synthetic profits**.

## Verified CI source-orchestration evidence

- [Original four-arm run #38016354281 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38016354281). Exact original manifest ZIP SHA256 passed; 6 unit tests orchestrator and 9 unit tests MTM passed. 3368 original unique fingerprint receipts in each of four isolated SQLite books, **13472 total**. Artifact `11656297239`, `cibo-p0-original-3368x4-canonical-paper-books-38016354281`.
- The initial four SQLite backups were byte-identical because no arm had any fills and all received the same data-absence classification. This was NOT a breach of account path isolation, but insufficient forensic labeling. Added `canonical_paper_scenario_arm` and binder audit events to force separately identifiable books and SHA256. New CI run [#38016450872](https://github.com/mezas3238-hue/qore-core/actions/runs/38016450872) to certify hash isolation; check its final conclusion and exact SHA before asserting PASS.
- Only unit/corpus/source gating is supported so far; no PF/real MTM DD from the 4×3368 experiment is known.

## Scientific exclusion accounting

In this historical source run, **no independently verified bid/ask M1/tick/JPY/fee/exit/Native MAX pack was supplied**. Therefore each opportunity receives a deterministic `PAPER_UNASSESSABLE_NOT_EXECUTED` receipt in each arm. This means:
- 13472 `NO_CAUSAL_EVIDENCE_PACK_FOR_SIGNAL` receipts = **4 scenario observations of 3368 missing-evidence source opportunities**;
- **NOT** 13472 CIBO trading rejects, bad entries, broker executions, financing denials, winners or losers;
- all paper opening counts 0, all broker fills 0 and no performance PF/DD published. Cash remains $60 in each untouched PAPER simulation solely because no orders were permitted.
- Do not substitute older 540/246 PF or infer performance from empty accounts.

## Mandatory next engineering

1. Historic per-signal native market evidence and externally authenticated broker source provenance (M1 VT31 484, H1 2229, H4 493, M15 162), entry side-correct BID/ASK, UTC NY/DST sessions, historical USDJPY and commissions.
2. Native broker-valued QDLE calculator and complete four **fresh** economic motor votes (not cached old outcomes); account epoch consistency and order queue.
3. Chronological **global** four-arm event scheduler with overlapping OPEN positions, full intratrade MTM marks, broker min-volume partials, ATR BE/trailing and exit semantics, pessimistic ambiguous intrabar stops; performance per Trader/year/PF/cash and equity DD/financing.
4. Integrate #746's verified canonical PaperQDLE implementation into #745 without changing research-only finance semantics; no competing active book.
5. Global quarantine and open-work failures must remain visible: never label Core certified by suppression.

**NO VPS, NO LIVE, NO MT5 broker fills; all four books are PAPER-only**.
