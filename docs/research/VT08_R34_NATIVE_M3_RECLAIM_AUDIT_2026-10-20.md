# VT08 R34 — Revalidación independiente de 301 recuperaciones del nivel CISD antiguo

Fecha 20 octubre 2026. Entrada: 5 ZIP R25 oficiales y 5 ZIP M3 RAW de GitHub Actions, sin alterar datos ni mirar PnL.

## Método
Para los 316 casos `post_cisd_lower_than_reanchored_low`, leer `first_close_reclaiming_old_level_available_at_utc`. Si nulo, clasificar NO_RECLAIM; si no nulo, buscar la vela M3 original del mismo mercado por `closed_at`, exigir estrictamente `close > old_cisd_bullish_breakout_level` con Decimal, y `first_new_low_after_reanchor_closed_at_utc <= reclaim_closed_at <= c3_decision_at_utc`. Clasificar recuperación en la misma vela del mínimo o posterior. No interpretar automáticamente como CISD auténtico.

| Mercado | Rupturas | Recuperaciones | Sin recuperación |
|---|---:|---:|---:|
| EURJPY | 74 | 71 | 3 |
| USDCHF | 60 | 56 | 4 |
| NZDUSD | 53 | 49 | 4 |
| CADJPY | 64 | 63 | 1 |
| USDCAD | 65 | 62 | 3 |
| **Total** | **316** | **301** | **15** |

301/301 barras originales localizadas, 301/301 cierres sobre nivel antiguo, 301/301 relojes causales válidos. 43 recuperaciones en misma vela del nuevo mínimo y 258 en velas posteriores. 0 anomalías detectadas. Estos resultados corroboran las cifras R25 mediante un lector independiente.

## Límites
`OLD_LEVEL_RECLAIM` es hecho físico, no `NEW_CISD_AUTHOR_VALIDATED`. `PROTECTED_SWING_SOURCE_COMPLETE=0`, 107 expedientes WAIT sin firmas independientes, 0 admisiones cognitivas y 0 fills broker. No atribuir edge ni certificar. Scripts y JSON sin RAW: `vt08_r34_reclaim_verify.py`, `vt08_r34_reclaim_verified_2026-10-20.json` en sesión. **VT08_NOT_CERTIFIED**; no LIVE, no merge, no sizing, no QORE-alpha, no holdout 7Y.