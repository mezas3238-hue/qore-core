# VT08 R37 — Gate causal estricto: primer CISD vs apertura C3

Fecha 2026-10-22. Auditoría **ejecutada** sobre cinco ZIP originales R25 de GitHub Actions; 2657 `case_id_sha256` únicos, 5 mercados. Script `vt08_r37_asof_gate.py` y JSON `vt08_r37_strict_asof_2026-10-22.json` de sesión. Sin OHLC licenciado publicado, sin PnL ni holdout.

## Resultados verificables

| Mercado | Primer CISD antes C3 | Primer CISD exactamente C3 | Reclaim antes C3 | Reclaim exactamente C3 | No reclaim |
|---|---:|---:|---:|---:|---:|
| EURJPY | 507 | 31 | 48 | 23 | 3 |
| USDCHF | 483 | 35 | 40 | 16 | 4 |
| NZDUSD | 519 | 31 | 37 | 12 | 4 |
| CADJPY | 481 | 35 | 45 | 18 | 1 |
| USDCAD | 514 | 21 | 51 | 11 | 3 |
| **Total** | **2504** | **153** | **221** | **80** | **15** |

La primera confirmación CISD está en el censo completo de 2657. El reclaim se mide **solo** en los 316 breaches del mínimo corregido R25. No sumar denominadores distintos ni asumir independencia de conjuntos. La salida JSON incluye los 80 case IDs de reclaim frontera; el censo completo se puede regenerar con el script.

## Contrato temporal fail-closed propuesto
- `available_at < C3.open` permite disponibilidad temporal previa, **pero NO certifica** CISD auténtico ni señal válida.
- `available_at == C3.open` significa **ORDER_UNKNOWN**: sin evidencia de secuencia del feed y modelo de ejecución, no afirmar fill al precio de apertura C3. Requiere decisión del arquitecto metodológico y contrato de latencia/orden. Estado `WAIT`.
- `available_at > C3.open` prohibido para decidir en C3.open.
- Este gate debe implementarse en validador operativo/admission manifest y probarse en CI; el informe no es implementación de producción.

**Bloqueos restantes:** Protected Swing, important POI, swing relevante, EQ, breaker, stop y target según TTrades; revisión A/B genuina, 27 campos causales, fills y Gates económicos preregistrados. **VT08_NOT_CERTIFIED**, sin merge/LIVE/sizing/holdout/QORE-alpha.