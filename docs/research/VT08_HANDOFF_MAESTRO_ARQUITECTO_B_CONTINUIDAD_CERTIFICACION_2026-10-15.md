# QORE CORE — VT08 | HANDOFF MAESTRO DEFINITIVO DE CONTINUIDAD (ARQUITECTO B)
**Corte investigado:** 15-oct-2026 · **Alcance:** Metodología TTrades original, cognitiva VT08 y Gates de certificación económica.  
**Propósito:** entregar TODO el contexto, código, resultados, problemas, decisiones irrevocables y pasos reproducibles al siguiente arquitecto.  
**Veredicto global al corte:** **VT08 NO CERTIFICADO**. Investigación de datos auténticos muy avanzada; semántica metodológica, admisión cognitiva genuina y resultados económicos siguen bloqueados.

## 0. Lee esto antes de cualquier prueba (restricciones Owner)
- Se certifica la **metodología VT08 y su cognitiva**, no una estrategia cuantitativa sustituta. Además debe aprobar PF, Drawdown, Sharpe, Sortino, expectativa, OOS, Monte Carlo, robustez y los demás Gates aplicables.
- **PROHIBIDO SIZING para certificar**: ni lotaje dinámico, ni leverage, ni compounding, ni ponderación de mercados o CIBO que transforme artificialmente PF/DD. Se pueden evaluar retornos homogéneos en unidades de **1R** definidas ex ante, nunca escalar el capital para rescatar resultados.
- **PROHIBIDO** usar VPS/LIVE/DEMO operativo/FundedNext, colocar órdenes, merge, abrir o reaprovechar el holdout de **7 años sellado**, modificar políticas de producción, inventar BID/ASK/fees/fills, seleccionar sólo ganadores o reabrir tests cerrados. Las credenciales DEMO cTrader que originaron los datos de histórico se utilizaron en adquisición histórica, **no** son permiso para operar.
- Cualquier D metodológica esencial que no se resuelva debe reportarse `NO_ESPECIFICABLE` o `NO_EVALUABLE`; no crear una regla nueva y llamarla TTrades. Code green no constituye licencia económica o de ejecución.
- **No extrapolar** los experimentos de VT31, CRT PURE, QORE Native ni QORE-alpha a VT08. Son identidades y ramas distintas. Ramas #764 y #765 siguen DRAFT y sin fusionar.

## 1. Repositorios, roles, versiones, fuentes de verdad
**Repositorio:** https://github.com/mezas3238-hue/qore-core

| Componente | Fuente concreta | Estado |
|---|---|---|
| **Arquitecto B**, cognitiva, verificaciones independientes, barreras | [PR #764](https://github.com/mezas3238-hue/qore-core/pull/764), rama `agent/vt08-5m-cognition-replay-20261010`, [issue #763](https://github.com/mezas3238-hue/qore-core/issues/763) | DRAFT, source/economics fail-closed. HEAD antes de ESTE documento: `457cfcab81c048a0bd6c23f82dde4fc700a85f8c` |
| **Arquitecto A**, método, corpus TTrades, datos fuente y CandidateEvent | [PR #765](https://github.com/mezas3238-hue/qore-core/pull/765), rama `agent/vt08-5m-methodology-source-20261010`, [issue #762](https://github.com/mezas3238-hue/qore-core/issues/762) | DRAFT. Último HEAD consultado: `362e1914469e6c3fac957b1708eb29f18d89445b`; volver a leer antes de desarrollar |
| Programa origen 5 mercados | [PR #634](https://github.com/mezas3238-hue/qore-core/pull/634) | otro frente de investigación, no merge automático |
| Ensayo final de una familia #787 | [issue #787](https://github.com/mezas3238-hue/qore-core/issues/787) | cerrado/superado; sus umbrales no reemplazan certificación global |
| QORE-alpha | [issue #798](https://github.com/mezas3238-hue/qore-core/issues/798) | otra identidad, sin traslado de Gates |
| Handoff histórico EXTENSO anterior | [VT08 handoff 14-oct, 38 KB](https://github.com/mezas3238-hue/qore-core/blob/agent/vt08-5m-cognition-replay-20261010/docs/research/VT08_HANDOFF_MAESTRO_CERTIFICACION_METODOLOGICA_COGNITIVA_GATES_2026-10-14.md) | fuente retrospectiva de 488 B01, 294 C3, 495 FVG/CISD y auditorías cognitivas de principio de mes; ESTE handoff añade rondas R1–R8 |

**Alcance Owner actual:** 5 mercados EURJPY, USDCHF, NZDUSD, CADJPY, USDCAD. Anclas H4 Owner 01/05/09 hora Nueva York; 13NY puede figurar en material de artículos, **no** es ancla Owner. Máximo una operación filled por mercado por día NY salvo nueva orden. Una ventana M30 C2 de 01:30–12:30 NY **no equivale a** una ancla H4 Owner 01/05/09: jamás mezclar los dos censos, ni inferir trades de C2.

### Fuente primaria metodológica
Referencias originales: TTrades *Relevant Swings* (21-mar-2026); *Equilibrium / Fractal Model* (10-oct-2026); *Timeframe Alignment* (30-jul-2025); *Breaker Blocks Simplified* (05-jul-2025); *Continuation Breaker* (03-ago-2025); *Price Targets* (23-may-2026); *Positional Entries*; *4 Hour Power of Three*. A mantiene matriz de URLs, apartados y citas breves. **No basta una URL o SHA en un JSON para demostrar relevancia correcta de un swing concreto.**

**Autoridad semántica por regla:** A = autor fuente primaria; B = inferencia documentada; C = formalización propia QORE, NO atribuible al autor; D = discrecionalidad/no resuelto. OWNER_POLICY distinto de SOURCE_A. Una estrategia inspirada en TTrades y llamada QORE-alpha exige identidad diferente y nuevo prerregistro, nunca falso PASS VT08.

## 2. Mapa de universos. No sumarlos ni llamarlos trades
| Universo | Conteo/evidencia | Qué ES | Qué NO ES |
|---|---:|---|---|
| B01 anterior H4/M15 | 11.655 anclas → 488 candidatos → 457 terminales en una implementación vieja | reconstrucción de aquella familia; CI B #38095654032 verificó 488 linajes | fills certificados del contrato nuevo |
| C3 y C4 pasado | 294 snapshots, 294/294 físicamente reconstruidos, CI B #38098119759 | evidencia física de geometría y relojes | 294 trades nuevos |
| Familia estrecha FVG/CISD M15 pasada | 495 recibos reconstruidos B, CI #38103539460 | source shape y proxies físicos | 495 setups autor válidos |
| Owner NY anclas exactas R2 | **11.650 observadas / 11.639 completas / 11 incompletas**; 0 OHLC mismatch | census RAW M3/M15 independiente B de anclas 01/05/09, [CI #38713809585](https://github.com/mezas3238-hue/qore-core/actions/runs/38713809585) 5/5 | fills, ni universo de 93.230 C2 |
| **Familia congelada M30 bullish C2→M3→C3 POS** | **93.230 ventanas C2**, [B R4 CI #38716419342](https://github.com/mezas3238-hue/qore-core/actions/runs/38716419342) 5/5 | 18.646 C2 de cada uno de cinco mercados, filtrado geométrico SIN PnL | 93.230 oportunidades ejecutables |
| Filtro bullish C2 | 83 incompletas, 0 mismatch, 85.312 sin geometría bullish single-low sweep, **7.835** geometría físicamente compatible | primer corte determinista; B recomputó del raw | validación PS/CISD original |
| Clasificación posterior de A | 4.702 sin forma PS, 476 múltiples PS proxy, **2.657** únicos PS proxy | clasificación A sobre los 7.835, positivos fuente físicamente revalidados B | B aún NO reimplementó independientemente el detector PS como semántica TTrades |
| Custodia física R7 | **88.276 source_bar_id** únicos dentro de mercado, **10.628 grupos C1/C2/H1** y **2.657** eventos positivos cotejados con A R3 | source OHLC/UTC/SHA comprobado B, [CI #38748150948](https://github.com/mezas3238-hue/qore-core/actions/runs/38748150948) 5/5 | decisiones cognitivas auténticas/fills |
| H1 precierre físico | 2.656 con 12×M15 PRE-C2; 1 CADJPY incompleto | contexto factual cerrado; no imputar faltante | swing relevante por definición del autor |
| EQ condicional B R8 | 2.657 `EQ_FULL=(H+L)/2` y 2.657 `EQ_CLOSE_LOW=(C+L)/2` matemáticamente verificados | ambos candidatos físicos; se auditaron offline ZIPs R4/R5 | selección de régimen EQ, target o stop |

**R8, matiz de evidencia:** auditoría **OFFLINE** B con [registro issue #763](https://github.com/mezas3238-hue/qore-core/issues/763#issuecomment-6196142170), entregables de esta conversación `VT08_B_R8_INDEPENDENT_EQ_AUDIT_2026-10-15.json` y `vt08_b_r8_independent_eq_audit.py` bajo `/mnt/data` (no alojados en GitHub al corte, retener/copiar por vía aprobada). Se cotejaron hashes JSON canónicos contra informe A; hubo **2.576** casos donde ambos EQ difieren numéricamente, **0** EQ autor seleccionados; una manipulación artificial de EQ se rechazó aun recalculando el SHA del reporte. **NO anunciar CI nueva o commit GitHub R8.**

## 3. Datos originales: localización y restaurabilidad
- cTrader 1.095d M15 por mercado: [Actions run #35934924907](https://github.com/mezas3238-hue/qore-core/actions/runs/35934924907), patrón `qore-vt08-cognitive-5m-fresh-{MARKET}-b2d33e1b4829d8b4afc76983decca8a99131403c`, archivo `market-evidence-1095d.json`.
- cTrader 1.095d M3 por mercado: [run #35941643396](https://github.com/mezas3238-hue/qore-core/actions/runs/35941643396), patrón `qore-vt08-m3-fractal-{MARKET}-bc1379d7661aac202495ec67afdd3098473ba723`, `m3-evidence.json`.
- R3 source completo y recibos 2.657: [A Actions #38715560333](https://github.com/mezas3238-hue/qore-core/actions/runs/38715560333), SHA A `394116f13449fc310d7fbc5f0b5f60aa1bb247d4`, artefactos `vt08-a-frozen-m30m3-firstfail-{MARKET}-{SHA}`.
- R4 catálogo con IDs bar y market mapping: [A Actions #38740699499](https://github.com/mezas3238-hue/qore-core/actions/runs/38740699499), SHA A `f61b5e7a931e2c057a0660f4702f11d55ebc58af`, `vt08-a-b-market-catalog-{MARKET}-{SHA}`. 5 artifacts documentados por mercado en reporte A R4.
- EQ R5 (ambas ramas): [A Actions #38747954308](https://github.com/mezas3238-hue/qore-core/actions/runs/38747954308), artifacts `vt08-a-author-conditional-eq-{MARKET}-57a6fa70f8a14ff26a6249b39d1f3e4725aa0a4c`.
- **CUIDADO:** esos artefactos GH Actions tienen retención usual de 30 días (hasta ~14-nov-2026 los nuevos). Antes de expiración, asegurar backup/restaurabilidad con hash, bajo licencias del broker y acceso adecuado. NO commitear feeds privados al repo público, no alterar SHA ni consultar el holdout sellado.
