# QORE-Alpha 2 / #837 — P0 offline private restore SHA verification contract (before implementation)

Date 2026-10-12. Scope: **only data custody**, NOT Alpha2 economic research, NOT broker execution.
Ancestor: master handoff commit `4a7640f5a0d23d82ced7d5279b52600273a4260c`; DRAFT PR #840, research branch only.

## Problem and frozen requirements

33/33 M5 original GitHub Actions artifacts have metadata-only digest/expiry witnesses in `alpha2_source33_artifact_expiry_inventory.py`, produced independently by Actions #38302743314. First original12 expiry **2026-12-16T00:21:18Z**; 21 newer artifacts follow in January 2027. **No authorized private vault or lawful retention confirmation is on record; these are temporary archives.**

A metadata SHA report proves neither (a) archive bits are stored in licensed permanent private storage nor (b) the private archive can be independently restored. Implement a strictly **OFFLINE verifier** usable only *after* an owner-approved licensed private custodian exports and separately restores exact ZIP bytes. **Do not automate the download, vault creation, upload, payment, broker or private-account access.** No original price data in CI, no sampling held-out outcomes.

### Input provenance and fixed layout

The external source inventory JSON must come from a separately authenticated GitHub REST original-run audit (run IDs, original code-heads, artifact IDs/digests), matching exact frozen 12+21 original roster and the original signed 33 reference. This local verifier cannot independently authenticate an arbitrary JSON file merely because its claimed SHA is syntactically valid; operator must preserve the signed external inventory witness.

The restorer supplies its **PRIVATE, local** restored folder:

```text
restored-root/
  ATLAS_ORIGINAL12/<12 exact original symbol>.zip
  ICMARKETS_NEW21/<21 exact original symbol>.zip
  META/atlas-aggregate.zip
  META/source33-manifest.zip
```

This means 35 downloaded/restored artifact ZIPs: 33 originals + Atlas aggregate + signed 33 manifest. The CLI never fetches network data, never extracts ZIP contents and never creates backups. The name mapping is exact; no fuzzy alias NAS100/USTEC or SP500/US500. Expect no extra artifacts in the fixed layout.

### Fail-closed acceptance

1. Validate inventory identity, exact 33 unique canonical symbols, frozen original-run IDs/HEADs, positive byte sizes, original GitHub SHA256 digest shape and exact original aggregate+signed manifest digest shape; do not accept partial lists or non-JSON structures.
2. Validate directories and restored ZIPs as ordinary physical local files. Reject missing/extra paths, symlinks and hardlinks, same-inode duplicate paths, missing/empty bytes.
3. Stream bytes through SHA256 (bounded memory). For 33 original ZIPs require both exact **byte count** and exact SHA digest from the GitHub inventory; for aggregate/manifest compare exact digest (their expected byte sizes were not recorded in the original metadata report).
4. Any unexpected value or mismatch MUST exit nonzero and produce no passing attestation.
5. A passing **local** rehash has only status `LOCAL_RESTORED_35_ZIPS_SHA_MATCH_SOURCE_INVENTORY_ONLY`. The fields `SOURCE_ARCHIVED_PERMANENTLY`, `license_verified`, `private_vault_authorized`, `independent_offsite_reader_verified`, and `UTC001_certified` remain **false**, irrespective of local hash success. GitHub CI is only small synthetic fixture validation; NEVER connect CI to a private vault or expose original ZIPs as artifacts.
6. External independent second-reader restore must be executed by different authorized operator/environment, alongside evidence of lawful license, versioned encrypted private custody, retention, access logging and per-year RAW/QUALITY internal SHA reconciliation. No automatic promotion of the source state based on the local verification alone.
7. W1 PATR, W2 PADE, W3 CMTRL remain locked/falsified on consumed periods. No reoptimization, no fresh OOS claim, no broker orders, no VPS/MT5/CIBO/Shared/QDLE/LIVE/MAIN.

## Unit and CI expectations

Synthetic positive 35 artifacts; missing symbol, extra symbol, corrupted bytes and same-size substitution, invalid inventory run head, symbolic link/hardlink, duplicate SHA/wrong length, tampered aggregate or signed manifest. Only isolated tiny artificial byte fixtures are allowed in GitHub Actions. No actual M5 prices or API/broker credentials in tests.

## Operations owner gate

Owner issue: [#837](https://github.com/mezas3238-hue/qore-core/issues/837). Further execution requires explicit rights/licensing and an authorized encrypted, access-controlled, versioned private destination. Until an actual independent restore attestation exists, **TEMPORARY_ONLY / ARCHIVE_BLOCKED** is the truthful status.