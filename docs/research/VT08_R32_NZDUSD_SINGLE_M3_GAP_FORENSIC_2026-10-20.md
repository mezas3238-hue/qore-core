# VT08 R32 — Peritaje de único gap M3 oficial (NZDUSD)

Fecha 2026-10-20. Se releyeron ZIP originales R25 y RAW M3, sin proxies ni PnL. `case_id_sha256=f318dd0d9f4082a449d99a90545ac632fac9ffae5e60e2ccf7238e666c4e83fa`.

- C2 abrió `2024-03-29T15:00:00+00:00`; primer breach del corrected low cerró `15:09 UTC`, con source bar ID `752092467015a0535bceb41d4df3888275c8d1afa65d774adbbcb23b28fde213`.
- C3 abre `15:30 UTC`; R25 reporta primer cierre reclaim del viejo nivel CISD disponible exactamente `15:30 UTC`, no antes.
- Única vela M3 ausente en la ventana C1+C2+C3: abrió `15:36 UTC`, índice relativo M3 `12` desde C2, en C3. **El breach ocurrió 27 minutos antes del slot faltante**. La cobertura de C2 fue completa.
- `reclaim_of_old_level_is_new_cisd=false`; `authentic_reformed_protected_swing=D_NOT_ASSESSED`, sin firmas A/B, no operación.

## Dictamen
`BREACH_TIMESTAMP_EVIDENCE_NOT_BLOCKED_BY_GAP` (el hueco C3 no afecta el hecho de que el breach R25 precedió C3). `C3_COMPLETE_COVERAGE=FAIL`; `NEW_AUTHENTIC_CISD=UNPROVEN`; `AUTHOR_PS=UNPROVEN`; `COGNITIVE_ADMISSION=WAIT`.

Reproducible con script `vt08_r32_nzdusd_single_gap.py` y resumen JSON `vt08_r32_nzdusd_gap_forensic_2026-10-20.json` de entorno de trabajo. Siguiente: verificar los 316 breaches individualmente contra M3 originales por fuente, resolver semántica PS y fuentes TTrades. No holdout, no LIVE, no merge, no QORE-alpha. `VT08_NOT_CERTIFIED`.