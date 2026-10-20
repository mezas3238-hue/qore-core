# VT08 R27 — Auditoría independiente RAW M3 ↔ M15 (20 octubre 2026)

## Procedimiento
Se leyeron los diez ZIP originales recuperados en R26, extrayendo `m3/{market}/m3-evidence.json` y `market-evidence-1095d.json` para cinco mercados. Se validó OHLC (low <= open/close <= high). Cada barra M15 se comparó contra cinco barras M3 con aperturas exactamente a 0, 3, 6, 9 y 12 minutos, agregando open inicial, máximo de highs, mínimo de lows y close final. Comparación numérica tolerancia 1e-7. Los intervalos incompletos no se aceptaron como prueba de coincidencia.

| Mercado | RAW M3 | RAW M15 | Grupos completos M15 | Grupos sin cobertura completa | Mismatch OHLC |
|---|---:|---:|---:|---:|---:|
| EURJPY | 372587 | 74499 | 74294 | 205 | 0 |
| USDCHF | 372012 | 74496 | 73911 | 585 | 0 |
| NZDUSD | 372002 | 74489 | 73945 | 544 | 0 |
| CADJPY | 372454 | 74498 | 74207 | 291 | 0 |
| USDCAD | 371923 | 74497 | 73853 | 644 | 0 |
| TOTAL | 1860978 | 372479 | 370210 | 2269 | 0 |

**OHLC invalidos:** 0 en M3 y 0 en M15 de los cinco mercados.

## Dictamen
`RAW_M3_M15_FULL_GROUP_AGGREGATION_PASS` para 370210 grupos completos. 2269 M15 sin cobertura completa permanecen `NOT_EVALUATED`, no necesariamente errores: examinar gaps de sesión, borde de retención y horarios. No confundir con censo A de 93230 C2 ni extrapolar a PS auténtico. No se observaron PnL, no se abrieron Gates cognitivos, no se alteró holdout ni QORE-alpha.

## Evidencia local
`vt08_r27_raw_m3_m15_crosscheck_2026-10-20.json` (resumen sin RAW) generado junto a la auditoría. R26: `docs/research/VT08_R26_CUSTODY_RECOVERY_2026-10-20.md`. Siguiente trabajo: clasificar los 2269 intervalos no completos por causa y reanudar fuente semántica de 316 nuevos mínimos (R25), 15 sin recierre y 107 expedientes ciegos. **VT08_NOT_CERTIFIED**.
