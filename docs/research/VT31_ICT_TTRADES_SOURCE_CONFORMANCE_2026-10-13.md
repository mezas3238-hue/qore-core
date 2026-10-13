# VT31 · Auditoría independiente de fidelidad: ICT 2023 vs TTrades Silver Bullet NY AM 2025

**13-10-2026 · Fuente congelada, examen DOCTRINAL solamente · Sin cambios de metodología, producción, G3 ni holdout.**

## Dictamen

**VT31 cleanroom es una hipótesis cuantificada inspirada en ICT, pero NO una reproducción fiel del modelo preciso Silver Bullet NY AM de TTrades (19-06-2025).** TTrades es una variante contextual concreta, **NO** puede atribuirse automáticamente como regla universal de ICT 2023. La prueba negativa direccional de 2.140 FVG de VT31 viejo **no refuta** ni la versión canónica ICT completa ni el modelo diferente de TTrades.

Prueba en NAS100 M1 desarrollo 3Y: **[GitHub Actions #38398253227 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38398253227)**, código/test/workflow SHA **`d3608c4cd4c56800f2d3fa3eec4448ba59b3df1c`**, **7/7 pruebas PASS**, Ruff/compile/market SHA256 PASS, evidencia artifact **`11814695513`**.

### Fuentes, jerarquía y alcance

1. **ICT primario:** [2023 Silver Bullet Time Based Trading Model, May 15](https://www.youtube.com/watch?v=tRq1hyGGtl4); [ASR de tercero para localizar pasajes, no reemplaza escuchar el vídeo](https://pickscribe.com/v/tRq1hyGGtl4/). Ventanas de 03–04, 10–11 y 14–15 NY; foco en DOL probable conocido antes de operar; previos high/low de sesión, día y semana, nuevas aperturas semanales/ineficiencias; «10 handles» es **framework de recorrido probable, NO beneficio por trade**; entrada con un FVG de la ventana, posición puede seguir abierta después del fin de la hora. **No se identifica en esta clase un único filtro obligatorio de barrido del H1 09–10 aplicable a las tres ventanas, ni una fórmula universal `SL=C2.wick−tick`.**
2. **TTrades primario/publicado por el propio educador:** [The AM Silver Bullet Strategy on NQ, June 19, 2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/). Marco **únicamente NY AM 10–11**, high y low de **H1 09:00–10:00 NY**, obligatoriedad de barrer uno de estos extremos **durante 10–11** antes de plantear setup, dirección **contraria al barrido** (barrido high→SHORT, low→LONG), objetivo **extremo opuesto del mismo rango H1**, confirmación desplazamiento hacia adentro del rango, entradas válidas por **breaker, order block, FVG dentro de estructura** (no sólo CE de primer FVG), SL **más allá del swing que causó desplazamiento**, días sin setup = cero trades. El texto presenta **una formalización más estrecha que el modelo general de ICT**.
3. **VT31 congelado para firma:** `src/qore/infrastructure/traders/vt31_ict_cleanroom/{cognition,operations,m1_execution,trader,contracts}.py` en commit **`78d4cdac0e09d1a6eef37b99c505ffc5098031fc`** y acta G3 r1.3 commit **`a446afa17ed6e411b8f0b6fc182b103a78959a97`**. El test anterior de 2140 usó **`LEGACY_C3_CLOSE_SOURCE_V0`**, con `VT31Trader()` construyendo COG/OPS por defecto; la versión `QORE_G3_MSS_CLOSE_V1_PROPOSED` es **OPT-IN, UNSIGNED**, y no ha sido evaluada económicamente.

## Matriz de diferencias inspeccionadas en código

| Control | Fuente ICT 2023 | TTrades AM 2025 | Código VT31 actual | Juicio |
|---|---|---|---|---|
| Horas operativas | 03–04 / 10–11 / 14–15 NY, DST | 10–11 NY solo | `contracts.py::window_bounds` usa las 3 y DST | Correcto respecto a ICT, **distinto de universo TTrades** |
| Referencia 09–10 NY | No es condición única/universal documentada para todas las ventanas | **H1 high/low 09–10 obligatorio** | `_OnlineCausalIndex` genera DOL: HIGH/LOW previa sesión NY cash (09:30–16:00), Asia NY clock (00–03), London (03–05); usa M15/H1/H4 genéricos sólo para vigencia/contexto; **sin H1 09–10 high/low como marco obligatorio** | **GAP CRÍTICO para fidelidad TTrades** |
| Barrido previo | Variantes de liquidez/DOL; no todo ejemplo exige el mismo patrón 09–10 | Primero debe barrer un extremo 09–10 en 10–11 | `cognition.py::assess` exige MSS M1 + DOL no mitigado; **no exige barrido 09–10 como disparador de entrada** | **GAP CRÍTICO TTrades** |
| Dirección | Determinar siguiente draw | **Reversa** al extremo barrido | MSS direccional por pivote local 3 M1 + desplazamiento `body≥1.25×median5`; contexto HTF verifica existencia M15/H1 pero **no exige que sus estados BULLISH/BEARISH coincidan con la dirección** | Política propietaria no equivalente |
| Target | DOL priorizado entre varias familias | **Extremo H1 opuesto 09–10** | Selección por `pools` de antigua NY / Asia / Londres y DOL mínimo a 10 puntos; no prioriza/opera específicamente `other_side_of_9AM_H1` | **GAP CRÍTICO TTrades** |
| Gatillo | FVG/delivery dependiente del ejemplo | Reentrada a rango con displacement, breaker/OB/FVG como opciones válidas | `operations.py` **únicamente** primer FVG 3 M1 cerrados con lado = COG; posterior `CE=(zone.low+zone.high)/2` como única precio de entrada hipotética | **Reduce variedad TTrades** y es hipótesis QORE, no fórmula universal ICT |
| Formación FVG | Durante ventana; otros elementos pueden ser previos | No impone en el artículo triplete exclusivamente dentro de hora ni solo M1 | `m1_execution.py` exige **C1/C2/C3 completamente dentro de ventana y M1 solamente** | Formalización QORE más rígida; no error de reloj |
| Potencial ≥10 puntos | Framework previsto contextual, **no** target mínimo o beneficio neto ejecutado | En 2025 destaca RR y rango 09–10, no impone el mismo ancla numérica | V0 `DOL−close(C3)` y V1 propuesta `DOL−close(MSS)` ≥10 | **Dos interpretaciones distintas, no equivalencia de ICT probada** |
| Stop | No fórmula universal `C2-wick` acreditada en clase base | **Swing que causó desplazamiento**, más allá del extremo | Ledger antiguo **sin stop**; G3 V1 propuesta **C2 mecha completa ±1 tick y mínimo 2 ticks**, aún NO integrada | **GAP CRÍTICO TTrades**, y V1 es hipótesis QORE |
| Gestión/exit | No obligatorio cerrar dentro de hora | Meta del otro extremo 09–10 | V1 propuesta DOL final y time-exit 15:55 NY, sin parciales/BE/trailing | Hipótesis nueva, distinta de TTrades |
| Instrumento | Ejemplos índices futuros ES | **NQ futuro** | 3Y NAS100 CFD M1, broker equivalencia **no verificada** | No confundir NQ y NAS100 como serie/ticks idénticos |

### Nueva falsación descriptiva cuantitativa sobre la cohorte antigua

**Diseño de prueba:** datos M1 originales `VT31_NAS100_OWNER_3Y_BASE_001` 1.059.784 M1, artifact `11459859004`, SHA256 **`0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`**, más ledger 2.140 primeros FVG antiguos artifact `11657461650`, 721 eventos NY AM. Se reconstruye H1 09:00–10:00 **exclusivamente con M1 previas**; se observa barrido de extremos 09–10 entre 10:00 y **antes del cierre de C2 del primer FVG** (para no atribuir barrido intravela C3 al pasado). Esta definición es **conservadora**, no prueba que otros casos no puedan ser entradas legítimas TTrades con un evento C3. El objetivo **se compara por igualdad exacta** entre DOL viejo y high/low opuesto 09–10, no por cercanía subjetiva. Pueden barrerse ambos lados; tales casos se clasifican AMBIGUOUS, sin asignar dirección ex post. **Sin outcomes, precio de fill, PnL, nuevas reglas o señal ejecutable.**

| Indicador | Cuenta |
|---|---:|
| Primer FVG old VT31 en NY AM 3Y | **721** |
| H1 09–10 completo reconstruible | **720** |
| H1 faltante o incompleto | **1 UNKNOWN** |
| **Barrido válido del lado contrario a la dirección antes de C3** | **222 / 720 = 30,83%** |
| No hubo barrido anterior a C3 | **328 / 720 = 45,56%** |
| Sólo hubo barrido de lado equivocado | **167 / 720 = 23,19%** |
| Ambos extremos barridos, dirección ambigua | **3 / 720 = 0,42%** |
| Barrido compatible **antes de C1** (restricción más estricta) | **209 / 720 = 29,03%** |
| DOL de VT31 **idéntico** al extremo opuesto H1 09–10 | **0 / 720** |
| DOL distinto del objetivo TTrades 09–10 | **720 / 720** |
| Barrido + DOL exacto conjunto | **0 / 720** |

**Interpretación principal:** en **al menos 498 de las 720 señales con H1 disponible** (328 sin barrido + 167 barrido dirección contraria al criterio + 3 de ambos lados no resolubles) no puede demostrarse la secuencia estricta TTrades antes de C3. Las otras 222 cuentan únicamente el barrido direccional previo; **NO prueban displacement de TTrades, breaker/OB, fill ni viabilidad económica**. Además **0 de 720** tiene el target exactamente en el lado contrario del H1 09–10; la diferencia de política de targets es inequívoca al nivel de precio registrado. El 0 es **igualdad de precios de target**, no 0 operaciones rentables. La cohorte no contiene la V1 nueva; no inferir su densidad futura.

**No convertir 222 en nuevos trades ni excluir 498 por PnL.** El screening negativo antiguo de 2.140 señales a 15min prueba el criterio **antiguo** de dirección, no una reproducción del TTrades 2025. Ni el resultado CE 301/2140 ni este censo validan rentabilidad de TTrades.

## Decisión / trabajo permitido

1. **No alterar G3 r1.3** ni presentar nuevo juicio sobre el PnL de V1. Mantener SHA originales en PR #896 y estado `PENDING_DUAL_SIGNATURE`, sin utilizar CI para fingir aprobaciones.
2. Clasificar correctamente modelos independientes: **`VT31_QORE_ICT_V0`** (replay antiguo), **`VT31_QORE_G3_V1_PROPOSED`** (nuevo marco MSS/CE/C2), **`TTRADES_NQ_NYAM_2025_MODEL`** (barrido H1 09–10, desplazamiento, target lado opuesto, stops swing, varias entradas). No llamar V0, G3 V1 o 222 casos “TTrades” o “ICT certificado”.
3. Si se decide iniciar una versión realmente fiel a TTrades, hacerlo con **nuevo modelo/branch y preregistro ANTES de usar outcomes**, no retocar retrospectivamente G3/2.140, ni buscar PF óptimo entre 222. Acreditar equivalencia NQ↔NAS100 y fuentes BID/ASK/OMS. Auditar con COG la jerarquía temporal swing/ruptura/fill sin lookahead. Sin esos gates, sólo puede concluirse **source-conformance mismatch**, no edge.
4. **Decisión científica:** la tesis «hemos comprobado que la Silver Bullet de TTrades no funciona» es **inválida**, pues el modelo que falló no era el modelo descrito por TTrades. Mantener `NO_GO` para gastar dinero en el **VT31 antiguo**, pero dejar nueva investigación de fidelidad como opción metodológica distinta sin afirmaciones de rentabilidad.

**Provenance:** archivo generado exclusivamente en `agent/vt31-ict-ttrades-doctrine-audit-20261013`; no edición de `cognition.py`, `operations.py`, `contracts.py`, ni G3, precios/capital/producción, holdout. Código ejecutado y evidencias de 7/7 tests en Actions #38398253227.
