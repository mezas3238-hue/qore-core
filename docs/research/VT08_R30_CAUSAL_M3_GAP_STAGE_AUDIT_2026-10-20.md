# VT08 R30 — Auditoría causal de huecos M3 por etapa C1/C2/C3

Fecha: 2026-10-20. Fuente: diez ZIP originales recuperados R26; reconstrucción independiente del proxy geométrico alcista M30 R29, no el ledger de 2657 candidatos oficiales. Sin PnL, sizing, holdout ni LIVE.

## Método
Para cada proxy `C2.low < C1.low` y `C1.low <= C2.close <= C1.high`, buscar 30 aperturas M3 exactas desde C1 hasta el final de C3. Clasificar jerárquicamente cada proxy con huecos: (1) cualquier hueco en C2, (2) C2 completo y cualquier hueco en C3, (3) solo huecos en C1. La clasificación es exclusiva y exhaustiva para 1043 proxies incompletos. Los contadores `gap_C1`, `gap_C2`, `gap_C3` por separado se superponen.

| Mercado | Proxies | C1-C3 completos | Con huecos | C2 incompleto | C2 completo, C3 incompleto | Solo C1 incompleto |
|---|---:|---:|---:|---:|---:|---:|
| EURJPY | 7922 | 7825 | 97 | 33 | 57 | 7 |
| USDCHF | 7479 | 7245 | 234 | 73 | 92 | 69 |
| NZDUSD | 7722 | 7478 | 244 | 90 | 108 | 46 |
| CADJPY | 7856 | 7699 | 157 | 51 | 79 | 27 |
| USDCAD | 7750 | 7439 | 311 | 132 | 135 | 44 |
| **Total** | **38729** | **37686** | **1043** | **379** | **471** | **193** |

## Causalidad y límites
No se permite usar información de C3 para admitir una decisión al cierre de C2. C2 incompleto bloquea comprobación de estructura M3 durante C2; C3 incompleto bloquea verificación de confirmación posterior; C1 incompleto puede bloquear la verificación completa del origen. El orden jerárquico de la tabla NO significa que C1 sea irrelevante si también falla C2/C3. Los datos M15 disponibles no sustituyen prueba M3.

El script reproducible es `vt08_r30_causal_gap_stage.py` y su resultado `vt08_r30_causal_gap_stage_2026-10-20.json` (generados localmente). Próximo paso indispensable: obtener ledger original R25 de 2657 IDs y cruzar timestamps exactos. No promover los 38729 proxies a señales ni certificar. **VT08_NOT_CERTIFIED**.