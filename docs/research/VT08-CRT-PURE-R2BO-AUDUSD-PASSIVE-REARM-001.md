# VT08 CRT PURE — R2-BO AUDUSD Passive Rearm Density

Identity: `VT08_CRT_PURE_R2BO_AUDUSD_PASSIVE_REARM_DENSITY_001`

Status: **SUPERSEDED PENDING CORRECTED REPLAY**.

R2-BO depends directly on the R2-BM passive lifecycle simulator. The previously recorded CAP1/CAP2 economics therefore inherit the same invalid post-fill M5 sequencing that conflicted with the frozen CRT M15 `STOP_FIRST` ambiguity rule.

The old numbers (including 164.13 trades/year for CAP1 and 167.60 trades/year for terminal rearm) are retained only in Git history and are not admissible evidence for promotion or certification.

R2-BO is now bound to the corrected R2-BM M15 lifecycle semantics and must be adjudicated only from the new replay.

Governance remains research-only: no certification, runtime, DEMO, LIVE, production, merge, or capital authority.
