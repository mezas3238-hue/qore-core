# VT08 R35 — Auditoría de mechas sin cierre tras ruptura del mínimo corregido

**Fecha:** 2026-10-20. **Identidad:** VT08 TTrades M30/M3, no QORE-alpha.

## Método independiente
Se leyeron cinco ZIP R25 oficiales (`full_source_case_index`, 2657 casos) y cinco ZIP RAW M3 cTrader. Se seleccionaron 316 rupturas `post_cisd_lower_than_reanchored_low=true`. Para los 15 casos sin `first_close_reclaiming_old_level_available_at_utc`, se buscaron todas las velas M3 desde el cierre de la primera ruptura hasta el instante de decisión C3, inclusive, y se contrastó `max(high)>old_cisd_bullish_breakout_level` y `max(close)>old_cisd_bullish_breakout_level` con `Decimal`. La comparación es estricta: igualdad no es superación. Sin PnL, inferencia intrabar, interpolación ni holdout.

## Resultado

| Mercado | Sin cierre reclaim | Mecha sobre nivel, sin cierre | Ni mecha sobre nivel |
|---|---:|---:|---:|
| CADJPY | 1 | 0 | 1 |
| EURJPY | 3 | 2 | 1 |
| NZDUSD | 4 | 4 | 0 |
| USDCHF | 4 | 3 | 1 |
| USDCAD | 3 | 3 | 0 |
| **TOTAL** | **15** | **12** | **3** |

Los otros **301** casos sí registran cierre M3 sobre el nivel CISD anterior, según R34. El informe JSON local contiene 15 `case_id`, UTC de breach/C3, nivel, máximo high y máximo close, y clasificación.

## Implicación cognitiva
Un high de mecha no equivale a un cierre confirmatorio. Tampoco un cierre por encima del nivel antiguo equivale automáticamente a un **nuevo CISD según TTrades**, ni resuelve Protected Swing o POI. El análisis R35 no cambia las admisiones: 0. Los 15 quedan en `NO_CLOSE_RECLAIM`, no se promueven a trades ni se eliminan retrospectivamente del censo. No usar datos de C3 posteriores a la decisión.

## Reproducibilidad
Script de sesión: `vt08_r35_nonreclaim_wick_audit.py` SHA256 `a312e74fffc981464c3f528bd03a694490a4a53d3a1daf0d10c839535aacecce`; JSON `vt08_r35_nonreclaim_wick_audit_2026-10-20.json` SHA256 `f2e5f81716b9627d7e71fe42fc6aa32f1c4174169c0ecf145c70d99dbdcb48a6`. Fuente: ZIP originales en custodia R26 y R31. No publicar OHLC licenciado.

**Siguiente:** adjudicación fuente TTrades de Protected Swing/CISD y revisión A/B real; después 27 campos causales y Gates económicos preregistrados. `VT08_NOT_CERTIFIED`; no merge, LIVE/DEMO/VPS, sizing ni QORE-alpha.