# VT31 M5 — Diagnóstico cognitivo de swing causante con fuente autoral, NO stop inventado
**15-OCT-2026.** Mandato Owner: certificación por metodología + cognitiva, NO rentabilidad ni sizing. Investigación child PR #959 sin merge ni LIVE.

## Evidencia ejecutada en fuente original
- **[CI GitHub Actions #38711574019 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38711574019)**, código ejecutado `b06f9a25e9256bcd614e64e08b84862a34e23e94`, **76/76 pruebas PASS** y Ruff PASS, fuente NAS100 1.059.784 M1 SHA256 original `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa` verificado (desarrollo ya observado, no OOS).
- **[Artifact #11961370684](https://github.com/mezas3238-hue/qore-core/actions/runs/38711574019/artifacts/11961370684)**, ZIP SHA256 `4d792d35bd6fabbdb61656ce70fe71bc702000b94f671d2d54df4e144a8f4c67`; guarda el casebook timestamp-by-timestamp y reporte íntegro.
- **Preregistro anterior al código** `ba9b50abca2ede965975f6aacfcdab8a057a3735`.
- Fuente TTrades [AM Silver Bullet 2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/): stop más allá del **swing que causó desplazamiento**. Fuente NO fija la identificación algorítmica de ese swing; **no** puede sustituirse por primer barrido H1, un pivote3 QORE o C2+tick sin fuente/version distinta.

## M5: pruebas cognoscitivas de incertidumbre causal, NO trades
Para los mismos **483 días** de contexto congelados, M4 #958 aporta el primer timestamp con FVG geométrico QORE y as-of causal. El testigo busca **SOLO swings locales pivote3 estrictos**, con la vela derecha cerrada ANTES del FVG; son **candidatos QORE**, no confirmación de que causaron el displacement.

| Resultado M5 del caso contextual | Casos | Decisión cognitiva segura |
| --- | ---: | --- |
| **0 pivotes locales QORE causalmente disponibles** | **189** | No inventar origen estructural |
| **1 pivote QORE** | **88** | Que sea único **NO prueba** que causó el displacement según TTrades |
| **Múltiples pivotes QORE** | **180** | Causalidad indeterminada, no elegir por conveniencia |
| **Sin FVG geométrico QORE previo válido** | **26** | No determina existencia de OB/Breaker/desplazamiento del autor |
| **Total** | **483** | Casos de método/COG, no entradas, no stops, no lotaje |

Primer ejemplo cronológico de cada tipo: primer pivote único **02-OCT-2023**, sin candidato **04-OCT-2023**, varios candidatos **13-OCT-2023**, sin FVG **31-ENE-2024**. Archivo incluye timestamps de confirmación y demuestra que el pivote no se adelanta antes de la vela derecha M1. Los 189/88/180/26 no son tasas de rentabilidad ni criterio cuantitativo de aprobación.

## Adjudicación por Gates
- **M4** cuatro familias mencionadas por autor pero algoritmos específicos y prioridades sin resolución en fuente: **NO_CERTIFIED**. Los 457 FVG del #958 son **solo geometría QORE**, no setup autoral completo.
- **M5** causative swing: **AUTHOR_CAUSATIVE_SWING_NOT_ESTABLISHED** en todos los casos de estudio, incluso cuando el pivot3 es único. Detectar candidatos y abstenerse evita fabricar un stop. **NO_CERTIFIED**; ningún stop numérico emitido ni lotaje, como ordenó Owner.
- **M6** issue [#897](https://github.com/mezas3238-hue/qore-core/issues/897) OPEN, exige firmantes COG/OPS independientes verificables. Sin esta aprobación no hay certificación integral de método/COG.

## Trabajo de cierre pendiente
1. Fuente primaria autoral o testigo de metodología adicional que defina en cada escenario **qué swing causó exactamente el displacement**; casos con dos swings candidatos exigen anotación causal independiente y NO TRADE si no se puede adjudicar.
2. Preregistrar interpretación por perfil/version de 4 familias M4 y prioridad, o etiquetar explícitamente alternativa **QORE propia** sin suplantar doctrina TTrades.
3. Retestar nueva política de M4/M5 **sin cambiar G3 original**, negativos de WAIT/REJECT/UNKNOWN y frontera COG/OPS.
4. Autenticar dos aprobaciones de M6 sobre SHAs exactos, registrar versión de perfil/contrato, solo después evaluar certificado de metodología + cognitiva; Trader Lab economía separado.

**Estado verificable:** **M5 TESTIGO DE INCERTIDUMBRE COGNITIVA PASÓ CI, PERO M5 AUTORAL Y VT31 METHOD_COG SIGUEN PENDIENTES**; no fingir certificado, no merge/live/DEMO/VPS/FundedNext, VT31 no calcula sizing.
