# VT08 R36 — Reloj causal de recuperación CISD versus apertura C3

Fecha: 2026-10-22. Ejecución independiente sobre los cinco ZIP originales R25 de GitHub Actions; 2.657 casos oficiales; sin PnL ni holdout. Script reproducible `vt08_r36_reclaim_decision_clock.py` y salida JSON `vt08_r36_reclaim_decision_clock_2026-10-22.json` (80 IDs SHA, sin OHLC).

## Método
Filtrar 316 `post_cisd_lower_than_reanchored_low=true`. Comparar `first_close_reclaiming_old_level_available_at_utc` con `c3_decision_at_utc` usando ISO 8601 UTC. Clasificación exclusiva: recuperación estrictamente anterior a decisión, recuperación exactamente en decisión, sin recuperación. Se exige diferencia múltiplo de 3 minutos y no negativa. No inferir tick ordering de timestamps iguales.

| Mercado | Rupturas | Recuperación antes de C3 | Exactamente en C3.open | Sin recuperación |
|---|---:|---:|---:|---:|
| EURJPY | 74 | 48 | 23 | 3 |
| USDCHF | 60 | 40 | 16 | 4 |
| NZDUSD | 53 | 37 | 12 | 4 |
| CADJPY | 64 | 45 | 18 | 1 |
| USDCAD | 65 | 51 | 11 | 3 |
| **TOTAL** | **316** | **221** | **80** | **15** |

Anticipación entre los 221: 3 min 71; 6 min 57; 9 min 32; 12 min 26; 15 min 24; 18 min 7; 21 min 4. Suma 221. Los 80 con igualdad de reloj **no** prueban que un cierre M3 pueda conocerse y ejecutarse simultáneamente al precio de apertura C3; requieren contrato as-of y modelo de latencia. `BOUNDARY_TIMESTAMP_ORDER_UNKNOWN=80`; **WAIT** hasta adjudicación fuente/ejecución. Tampoco se afirma que el reclaim del nivel antiguo sea CISD nuevo auténtico. No elevar 221 a operaciones: POI/PS/CISD/stop/target/firmas faltan.

**Estado:** VT08_NOT_CERTIFIED, 0 admisiones cognitivas, 0 fills. No merge, no LIVE, no sizing, no QORE-alpha.