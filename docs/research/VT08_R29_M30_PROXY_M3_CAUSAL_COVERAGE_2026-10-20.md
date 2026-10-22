# VT08 R29 — Cobertura M3 de ventanas causales M30 (20 octubre 2026)

## Alcance
Análisis independiente de diez ZIP RAW originales de R26. Se agregaron barras M15 contiguas a M30 (UTC, minuto 00/30), sin rellenar huecos. Proxy alcista preliminar: C2.low < C1.low y C1.low <= C2.close <= C1.high. Este proxy NO incluye separación swing relevante, POI, PS, CISD, breaker, EQ, sesiones, selección de geometría ni deduplicación oficial. **NO equivale a los 2657 candidatos oficiales**. Se verificó cobertura exacta de 30 slots M3 para C1+C2+C3 (90 minutos), sin inspeccionar precios futuros, PnL o holdout sellado.

| Mercado | Proxies M30 | C1-C3 M3 completos | C1-C3 M3 con gap | C2-C3 M3 con gap |
|---|---:|---:|---:|---:|
| EURJPY | 7922 | 7825 | 97 | 90 |
| USDCHF | 7479 | 7245 | 234 | 165 |
| NZDUSD | 7722 | 7478 | 244 | 198 |
| CADJPY | 7856 | 7699 | 157 | 130 |
| USDCAD | 7750 | 7439 | 311 | 267 |
| **TOTAL** | **38729** | **37686** | **1043** | **850** |

Cobertura M3 completa en el proxy C1-C3: 37686/38729 = 97.31%. 1043/38729 = 2.69% con al menos un slot M3 ausente; estos casos deben bloquear adjudicación cognitiva sin reconstrucción de fuente. Los 850 con gap en C2-C3 son subconjunto de 1043. Esta cifra NO es tasa de pérdida de los 2657 candidatos ni una estimación de rendimiento.

## Reproducibilidad
Código de análisis local: `vt08_r29_causal_coverage.py`. Resumen sin barras RAW: `vt08_r29_causal_coverage_2026-10-20.json`. Censo completo de gaps R28 y hashes R26 documentados en el mismo branch. Se requiere unión causal con ledger original de 2657 candidatos, no inferirla por este proxy.

## Próximo gate
Cruzar identificadores y timestamps exactos del ledger oficial con huecos M3, emitir `COVERAGE_PASS/FAIL/UNKNOWN` por candidato; luego auditar 316 rupturas de mínimo corregido R25 y semántica Protected Swing. Certificación VT08_NOT_CERTIFIED; sin LIVE, sin merge, sin sizing, sin QORE-alpha.