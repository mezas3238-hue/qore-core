# VT08 CRT PURE — R2-BM AUDUSD Passive Entry Economics

Identity: `VT08_CRT_PURE_R2BM_AUDUSD_PASSIVE_ENTRY_ECONOMICS_001`

Status: **SUPERSEDED PENDING CORRECTED REPLAY**.

The previously recorded R2-BM economics are not admissible evidence. The passive lifecycle resolver used M5 sequencing after fill, which could allow a target hit on one M5 to win even when the structural stop was also hit later inside the same M15. That violated the frozen CRT rule:

`same M15 STOP/TARGET ambiguity -> STOP_FIRST`.

The implementation has been corrected so each post-fill M15 bucket is adjudicated conservatively: if both stop and target are reachable anywhere inside that M15, STOP wins. In addition, a passive entry may not claim a target touch from the same M5 range that established the fill, because the target may have occurred before the fill inside that bar. The same-fill-M5 stop is still charged conservatively. BE_CLOSE_075 remains close-confirmed and becomes effective only on the next M15.

The earlier headline values (including CONF_RANGE_MID PF 1.11891) must not be used for promotion, comparison, certification, or downstream claims until the corrected replay completes.

Governance remains research-only: no certification, runtime, DEMO, LIVE, production, merge, or capital authority.
