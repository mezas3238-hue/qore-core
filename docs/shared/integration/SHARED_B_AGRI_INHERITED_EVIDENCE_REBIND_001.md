# SHARED B AGRI INHERITED EVIDENCE REBIND 001

Purpose: bind B-14 to immutable pre-split agricultural provider evidence without
rewriting its historical origin.

Original evidence:

- run: 36623645085
- artifact: 11059457712
- SHA: 0ce7a2938fa50328d8ab569f47c776852dd5eafe
- branch: agent/qore-core-stack-v2-shared-001

Common A/B split checkpoint:

- 7d1b54cfa5453c0eb5c0662438ed15e7d656da61

GitHub comparison proves the original AGRI-1 SHA is an ancestor of the common
checkpoint. The rebind workflow additionally proves the checkpoint is an
ancestor of the current B head.

The rebind does not claim that B generated the old evidence. It produces a
B-native lineage wrapper that preserves:

- original run/artifact/SHA/branch;
- original artifact digest;
- provider sensor count 177;
- conceptual agricultural universe count 16;
- provider candidate count 0;
- no fresh holdout;
- no broker/productive authority.

This is provenance repair only. B-14 remains EXTERNALLY_BLOCKED until an
authorized provider exposes agricultural/soft/livestock candidates or another
lawful data source is explicitly admitted.
