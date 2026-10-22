# VT08 R31 — Cruce oficial 2.657 case IDs R25 vs M3 RAW

Fecha: 2026-10-20. Auditoría ejecutada contra cinco artefactos R25 `full_source_case_index` originales de Actions run 39338842612, y cinco ZIP RAW M3 de run 35941643396. **A diferencia de R29/R30, estos son los 2.657 candidatos oficiales, no proxies M30.**

## Método reproducible
Para cada `case_id_sha256` original y `c2_opened_at_utc`, comprobar exactamente 10 aperturas M3 en C1 (−30 a 0 min), 10 en C2 (0 a 30) y 10 en C3 (30 a 60). Rechazar interpolación, velas sintéticas, redondeo de timestamp y datos de futuro. Las ventanas C3 son comprobación de integridad, no evidencia admisible antes de C3. Script reproducible `vt08_r31_official_case_coverage.py`, ledger resumen `vt08_r31_official_case_m3_coverage_2026-10-20.json` con case IDs y contadores, sin OHLC licenciado.

| Mercado | Casos oficiales | C1-C3 completos | Casos con gap | Breaches R25 corrected-low | Breaches con gap |
|---|---:|---:|---:|---:|---:|
| EURJPY | 538 | 538 | 0 | 74 | 0 |
| USDCHF | 518 | 518 | 0 | 60 | 0 |
| NZDUSD | 550 | 549 | 1 (C3) | 53 | 1 |
| CADJPY | 516 | 516 | 0 | 64 | 0 |
| USDCAD | 535 | 535 | 0 | 65 | 0 |
| **TOTAL** | **2657** | **2656** | **1** | **316** | **1** |

## Dictamen
Cobertura completa C1-C3: 2656/2657 (99.9624%). El único gap está en C3 NZDUSD y también pertenece al conjunto de 316 breaches R25. No inferir que invalida necesariamente el breach: requiere cotejar timestamp de barra fuente de la ruptura y slots concretos ausentes. Los 2657 tienen C2 M3 completo, pero esto NO demuestra fidelidad de TTrades, Protected Swing, POI, CISD, cognitiva o fills. El único gap se mantiene en cuarentena para evidencia C3.

R29/R30 (38729 proxies M30) no son el universo oficial: sus 1043 gaps NO deben atribuirse a los 2657. Próximo paso: revisar la identidad del único caso NZDUSD, reconstruir los 316 breaches por sus bar IDs R25, cerrar semántica PS con fuentes originales, y mantener 107 expedientes WAIT hasta firmas reales A/B.

**VT08_NOT_CERTIFIED; 0 admisiones cognitivas, 0 broker fills, no LIVE, no merge, no holdout, no QORE-alpha.**