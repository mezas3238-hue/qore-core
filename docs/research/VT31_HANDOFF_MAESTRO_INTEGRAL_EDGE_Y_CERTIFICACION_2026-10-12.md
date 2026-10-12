# QORE CORE — VT31 NAS100 — HANDOFF MAESTRO INTEGRAL DE RECONSTRUCCIÓN, COGNITIVA, METODOLOGÍA Y DECISIÓN DE EDGE

**Corte documental: 12 de octubre de 2026. Responsable saliente: Arquitecto 1 (COG / investigación causal). Destinatarios: siguiente arquitecto de VT31, Arquitecto 2 (OPS), dirección de QORE Core.**

**Veredicto obligatorio:** **EDGE ECONÓMICO REAL NO DEMOSTRADO · NO CERTIFICADO · NO LIVE · NO VPS · NO ORDENES AUTORIZADAS.** Existe una reconstrucción M1 y una investigación seria, pero NO un Trader rentable científicamente probado. El siguiente trabajo **NO ES agregar más cognitiva**: es decidir con evidencia económica y fidelidad metodológica si VT31 merece existir o debe ser retirado.

**Repositorio:** `mezas3238-hue/qore-core`. **Issue de coordinación entre arquitectos:** [#727](https://github.com/mezas3238-hue/qore-core/issues/727). **Este documento prevalece como índice de continuidad sobre los handoffs anteriores**, que permanecen como evidencia histórica; no sustituye el examen de los artefactos originales. **No introducir lógica del antiguo VT31 en esta reconstrucción.**

---

## 1. Mandato irrevocable del propietario

1. **Un único Trader registrado llamado `VT31`**, activo en **NAS100** en investigación. No inventar `VT31_LONDON` y `VT31_NY` como Traders separados: son modalidades internas de UNA identidad, UNA memoria cognitiva y eventual UN libro de exposición y riesgo.
2. **Dos modelos de sesión: LONDRES y NUEVA YORK.** Nueva York tiene las subventanas AM/PM; las tres ventanas Silver Bullet expresadas en `America/New_York` con DST de EE. UU. son **03:00–04:00**, **10:00–11:00**, **14:00–15:00**. La fecha local y el horario de verano importan.
3. **M1 es temporalidad EJECUTIVA OBLIGATORIA**: cierre M1, MSS, desplazamiento, FVG de tres M1, precio CE y vida de orden. M15/H1/H4 sólo contexto de estructura/HTF; no ejecutar con un FVG M5/M15 disfrazado de M1.
4. Reinicio completo del VT31 anterior: **no** copiar lógica R2.2, COMP, TTrades, estado obsoleto ni sus resultados retrospectivos. El reset original limpió aproximadamente 668 archivos heredados en la rama aislada; preservar el histórico como testigo, no como operador.
5. Arquitectos colaboran **por GitHub Issue #727, PRs y evidencias CI**, no mediante afirmaciones de progreso sin commit/artefacto.
6. Entregar rentabilidad **demostrada**, no candidatos FVG “rentables” por denominación. Ninguna autorización LIVE/real, CIBO/QDLE/Shared y VPS hasta pasar compuertas de método, quote execution, cartera, riesgo y certificación.
7. El propietario aportó **captura MT5 NDX100 Bid 30853.00 y Ask 30854.60**, y solicitó repetir la prueba con ese dato: se hizo mediante escenario de **spread constante 1.60**, debidamente etiquetado como hipótesis, NO histórico real de BID/ASK.

## 2. Dictamen de negocio — prioridad actual P0

**La única pregunta prioritaria hoy es si la metodología implementada genera expectativa neta positiva, robusta y ejecutable.** A día de hoy NO lo sabemos. Las 1,059,784 velas demuestran funcionalidad de ingeniería y falsabilidad, no edge.

**Mi recomendación al siguiente arquitecto:** realizar **una etapa final delimitada de investigación** y presentar un dictamen `CONTINUAR_CON_EDGE_VERIFICADO` / `INSUFICIENTE_EVIDENCIA_POR_DATOS` / `RETIRAR_VT31`. No buscar indefinidamente un PF ganador por filtros nuevos, no reutilizar la rentabilidad del VT31 antiguo ni aumentar el número de entradas como métrica objetivo. Distinguir:
- **Fidelidad ICT / coherencia causal**: ¿el algoritmo reproduce un setup verificable de Silver Bullet original o es una formalización QORE distinta?
- **Edge económico**: ¿produce operaciones realmente elegibles, con costes, stops, targets y drawdown medibles?
- **Validez de datos**: ¿la base disponible puede contestar esa pregunta, o sólo es OHLC M1 insuficiente?

**Decisión actual:** AÚN NO RETIRAR por ausencia de prueba, pero **NO INVERTIR MÁS EN COGNITIVA** antes de resolver método + ejecución. Si un estudio económico completo y previamente definido muestra falta de edge o riesgo inadmisible, recomendar retirada, no prolongación automática.

## 3. Estado de GitHub y cadena correcta de integración — REVISADO 2026-10-12

| Rama / PR | Propósito | Estado al corte |
|---|---|---|
| `agent/vt31-ict-cleanroom-rebuild-20261009` / [PR #750](https://github.com/mezas3238-hue/qore-core/pull/750) | Coordinadora OPS, COG+OPS integrado M1, sensores, cancelación P0 corregida, auditoría ofertas, orden ficticia | **DRAFT**, base `main`, cabeza `84fdd75c345a40779a2e1c2bef2876ae5e7798a1`. No merged a main. |
| `agent/vt31-ict-cleanroom-cognition-single-trader-20261009` / [PR #751](https://github.com/mezas3238-hue/qore-core/pull/751) | Desarrollo original COG autónomo y pruebas | DRAFT; las piezas fueron **integradas mediante commits revisados** `02ad7f3d1f7b065d9ee224032a404f4e85da04b0` y `26adc8a446b38d4e5bf7f03243bee6a6c724e83b` en la coordinadora de investigación; PR puede seguir formalmente abierto. **No hacer doble cherry-pick.** |
| `agent/vt31-cog-revocation-forensics-20261010` / [PR #752](https://github.com/mezas3238-hue/qore-core/pull/752) | Sondeo 3Y read-only de causas revocación | DRAFT, base coordinadora OPS, cabeza `03fb9f48620c598ae07c3f147eb55bdffa86d354`. |
| `agent/vt31-ab-research-20261010` / [PR #753](https://github.com/mezas3238-hue/qore-core/pull/753) | Rama contrafactual A/B pivote MSS roto vs swing contrario protegido, no producción | DRAFT, base PR #752, cabeza `949a4fdd335eb9943ea6436f6136415029aff599`. |
| `agent/vt31-bidask-tick-evidence-20261012` / [PR #833](https://github.com/mezas3238-hue/qore-core/pull/833) | Escenario 1.60 fijo sobre el A/B M1 y auditor puntual de Bid/Ask | DRAFT, base PR #753, cabeza **`e51d1bc8a7d14514507d343875b273e07e9afa6a`**, mergeable clean cuando se comprobó; incluye archivo de auditor ticks **todavía sin prueba independiente suficiente**. |
| **`agent/vt31-master-handoff-20261012`** | **Custodia de continuidad**, esta documentación sobre base PR #833, SIN cambio de producción | Rama nueva exclusivamente documental. Revisar PR de custodia y enlazarla desde Issue #727; no equiparar publicación documental con integración productiva. |

**Importante:** Son PRs encadenados de investigación; no son cinco estrategias distintas ni cinco Traders. Las ramas de research pueden quedar separadas para salvaguardar integridad causal. No fusionar a `main` por tener un fast runner verde. OPS es propietario de `operations.py`, `order_lifecycle.py`, oferta/orden y broker; COG de `cognition.py` y sus sensores; no editar propiedad ajena sin Issue/review.

## 4. Línea temporal de trabajos realizados (todo el período cleanroom)

**09/10 — reconstrucción desde cero:**
- Fijadas ventanas originales New York con DST, contratos inmutables `M1Bar`, `CognitiveDecision`, `FvgCandidate`, `SessionId`, estados OPS, fuente económica separada.
- Se estableció `VT31Trader` único, memoria M1 compartida Londres/NY, rechazo de huecos de datos, ventanas incompletas, ningún broker/order routing. Contexto M15/H1/H4 en base a **velas M1 completamente cerradas**, nunca lookahead; liquidity sources NY cash previo, Asia NY-clock y London early; fuentes confirmadas, no barridas.
- COG independiente: estructura MSS M1 causal + desplazamiento experimental, objetivo direccional DOL, tesis MSS persistente hacia FVG de M1 posterior con revalidación de objetivo/pivote; tres FVG M1 dentro de ventana en OPS. `_OnlineCausalIndex` permitió escanear ~1.06 M M1 sin coste cuadrático.
- Real M1 de 3Y replayado, candidatos reconstruidos sin fills ni PF; Source SHA congelada.
- Implementados sensores pasivos I/O por componente (M1 feed; M15/H1/H4; niveles NY cash/Asia/London; sweep; MSS, DOL, tesis persistente; OPS FVG/candidato; BID/ASK, ACK y CIBO desconectados correctamente reportados).

**09/10 — reparación efectiva entre arquitectos:**
- Sensor COG independiente encontró **937 FVG fuentes únicas** y **7,648 observaciones M1 repetidas** con OPS research pending pese a `COG=None`; NO eran órdenes/losses.
- OPS corrigió cancelación fail-closed de oferta pendiente al desaparecer o cambiar prueba cognitiva. Ensayo integrado [#38018856150 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38018856150) demostró **CERO fuentes pendientes sin COG** en 3Y y 0 observaciones del fallo; 2,140 primeros FVG mantenidos. **P0 antiguo CERRADO**, no reabrirlo por confusión con la cifra histórica.
- Otra restricción OPS cancelaba 819 FVG sólo por MSS posterior de igual dirección, sin soporte ICT. Fue retirada en rama de investigación; preservada la reevaluación de COG M1, sin elegir trades por PnL. Ensayo oferta [#38018602495 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38018602495) dio estados finales.

**10/10 — investigación causal de invalidaciones:**
- Prototipo COG read-only y [CI #38020203387 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38020203387), ~29 tests y misma identidad por ventana. Identificadas causas de revocación de hipótesis, SIN tocar sistema operativo ni simular fills.
- A/B preinscrito ANTES de leer resultados: A OPS existente vs B swing OPUESTO causal protegido de 3-M1 confirmado antes del MSS. Primer FVG contrario después de MSS contrario desplazado dentro de la MISMA ventana (no fugas después de 04/11/15 NY); misma CE/FVG/DOL para las dos ramas; UNKNOWN si no se conoce swing, geometría o secuencia M1.
- [CI #38040127136 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38040127136), 29 tests, artefacto **11664804507**, 2,140 pares candidatos. Gate científico de B **FALLÓ**, por 31.31% desconocidos frente a máximo preregistrado 10%, aunque B sobrevivía más al CE.
- Se redactaron y comunicaron reportes de metodologías, etiqueta ICT explícito vs formalización QORE vs hipótesis B, disciplina de comparaciones múltiples, destino precio tras CE sin declarar wins.

**10–12/10 — evidencia de broker de usuario y escenario de spread:**
- Captura MT5 HISTORY anterior: una sola operación ejecutada **NDX100 BUY 0.01 lot**, entrada **30852.60**, salida **30848.08**, precio −4.52 puntos, bruto **−0.45** unidades monetarias de cuenta, comisión visible **0.00**. Observación parcial compatible con ~10 unidades/índice por 1 lot completo, **NO contrato oficial**. [Nota OPS](https://github.com/mezas3238-hue/qore-core/blob/84fdd75c345a40779a2e1c2bef2876ae5e7798a1/docs/research/VT31_NDX100_MT5_USER_SCREENSHOT_ECONOMICS_2026-10-10.md). No reutilizar comisiones de FX/metales para índice. CI OPS [#38019929182](https://github.com/mezas3238-hue/qore-core/actions/runs/38019929182).
- Captura MT5 QUOTES actual: **NDX100 BID 30853.00, ASK 30854.60**, spread **1.60 puntos**. Screenshot es cotización de UN instante; zona horaria del terminal, servidor, timestamps reales y símbolos NAS100↔NDX100 siguen sin contrato reconciliado.
- Petición directa propietario: usar esa cotización como BASE para prueba. Se ejecutó sobre **TODO el M1 3Y** como **hipótesis de spread fijo**: precio M1 histórico tratado provisionalmente como MID, sintético BID = M1−0.80 y ASK=M1+0.80. **No** insertar precio absoluto 30853 en velas antiguas. Larga CE contra ASK, corta CE contra BID.
- [CI #38257774657 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38257774657) **35/35 tests**, artefacto **11750991244**. Resultado **A 232 y B 577** primeros CE M1 source compatibles con lado sintético. B-only 372; A-only 27; neto +345 / +16.1215pp. B sigue 31.31% indeterminado; FAIL de gate. No fills ni PF.

**Antiguo VT31 R2.2 / números históricos:** menciones de **55 operaciones / PF 1.63 / DD aprox. 21R** y unas **23 pérdidas consecutivas** provienen de otra implementación metodológica, sin controles cleanroom/broker, y **NO son evidencia económica nueva**. No certifican ni desacreditan por sí solos el ICT original; PROHIBIDO mezclarlos con 2,140 actuales.

## 5. Contrato de datos y universo explorado

**Entrada científica INMUTABLE:** `VT31_NAS100_OWNER_3Y_BASE_001`, NAS100 M1, **2023-10-01 inclusive → 2026-10-01 exclusivo**, **1,059,784** velas cronológicas reales con `opened_at,closed_at,open,high,low,close,period`. Artefacto GitHub Actions **11459859004**, SHA-256 exacto:

```
0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa
```

Sin series BID/ASK históricas en esta fuente. No equiparar `NAS100` OHLC con MID verdadero ni `NDX100` MT5 de usuario sin certificado de fuente. No completar velas faltantes con sintéticos. 60 M1 consecutivos por fuente por sesión o etiqueta `INCOMPLETE`, sin setup FVG simulado. Inicio/fin NY con `zoneinfo America/New_York` y DST. **2,286** ventanas completas: LON 774, NY AM 771, NY PM 741. **137,160** llamadas fuente COG + **137,160** llamadas OPS, relación 1:1, fuente mercado 1,059,784. **FRESH HOLDOUT PERMANECE SELLADO**. Este 3Y es *desarrollo/research* con decisiones examinadas: nunca presentarlo como holdout independiente.

**Fuente principal ICT conocida:** lección 2023 Silver Bullet time-based, video indicado en OPS handoff [ICT 2023](https://www.youtube.com/watch?v=tRq1hyGGtl4). Distinguir material primario verificable de resúmenes de terceros, DeepSeek y nuestras definiciones inventadas. Ventana horaria / retorno hacia FVG pueden ser compatibles; elección de MSS micro-pivote 3M1, multiplicador de desplazamiento 1.25×, punto CE único, mínimo 10 puntos y stop swing 3M1 son **formalizaciones QORE/hypotheses**, nunca doctrinas universales ICT sin cita exacta.

## 6. Código real que debe entender el siguiente arquitecto

`src/qore/infrastructure/traders/vt31_ict_cleanroom/`:
- `contracts.py`: DTOs, tiempo UTC/NY DST, side LONG/SHORT, `M1Bar`, `CognitiveDecision`, `FvgCandidate`, estados de research. Invariantes de nivel, estructura y timestamps sin futuro. Tres `SessionId` nombran VENTANAS, nunca Traders.
- `m1_execution.py`: FVG de tres velas M1 consecutivas cerradas, horario fuente, geometría y rechazo de timeframe M5/M15 como ejecución. No trade execution.
- `cognition.py`: `VT31CleanroomCognition`, índice online, confirmed pools previo NY cash/Asia/London, HTF M15/H1/H4 as-of, cambio de estructura `M1 MSS`/desplazamiento, objetivo DOL, mantenimiento MSS anterior, revalidación/abstención causales. `structure_break_confirmed_at` original preservado aun cuando FVG aparece M1 posterior. Revisar `_confirmed_break`, pivotes 3M1 y DOL jerarquía con doctrina.
- `trader.py`: `VT31Trader` único, `on_closed_m1`, un estado cognitivo para ambas sesiones, `_windows` por día y ventana para traza; no abrir cuenta/subtrader por ventana. Fuera de source hour alimenta contexto sin crear oferta.
- `operations.py`: `IctSilverBulletOperations`, selecciona primer FVG oportuno y controla estado de fuente, CE research, DOL, nueva tesis o revocación `COG=None`, expiración al cierre de hora. **Cierre correcto de P0**; no forzar una orden de broker cuando hay wick M1.
- `cognitive_telemetry.py`: auditores pasivos de input/output/calls/gates por módulo; no evalúan un LLM independiente. `M1_THESIS_REVALIDATION`, `M1_MSS_DISPLACEMENT`, `DOL_ARBITRATION`, `COGNITIVE_DECISION`, `OPS_M1_FVG`, `OPS_CANDIDATE`; `BID_ASK_FILL`, `EXTERNAL_EXECUTION_ACK`, `CIBO_QDLE_ECONOMICS` 0/no conectados. H4 disponible como contexto, **NO** se ha demostrado aporte como condición de entrada.
- `order_lifecycle.py`: `SourceLimitOrderAudit`, `TwoSidedQuote`, `ExternalExecutionAck` como contrato auditado, **NO envía órdenes**, quote crossing ≠ broker fill. Expiración del setup nunca liquidación automática de una posición previamente confirmada. Cancel/ACK tardío requiere reconciliación broker.
- `fixed_spread_quote_scenario.py`: hipótesis solicitada por propietario, observación BID/ASK 30853.00/30854.60 y MID M1 ±0.80, **sólo prueba de precio**.
- `quote_tick_science.py`: **prototipo de parser/auditor pasivo de ticks**, creado en rama del escenario; su validez de extremo a extremo, tests propios, integración real y cobertura NO están acreditados en CI #38257774657. **NO tratarlo como pipeline certificado, ni usarlo para fills sin revisión rigurosa.**
- Archivo separado OPS `observed_broker_economics.py` existe en la rama coordinadora OPS con transcripción de una operación MT5 real, no contrato para NAS100 3Y; comprobar su presencia/merge antes de importarlo desde rama #833.

Scripts principales:
- `scripts/vt31_ict_cleanroom_cog_real_3y_fast_v1.py` — full 3Y COG, snapshot de origen y sensor.
- `scripts/vt31_ict_cleanroom_joint_m1_offer_audit_fast_v1.py` — auditor OPS candidato FVG, estado fuente y hora.
- `scripts/vt31_ict_cleanroom_cog_revocation_forensics_3y_fast_v1.py` — por qué revocó COG/OPS, sin introducir PnL.
- `scripts/vt31_shadow_opposite_pivot_ab_v1.py` — rama B prototipo protegido, efecto contrario desplazado + primer FVG en misma hora.
- `scripts/vt31_shadow_ab_3y_runner.py` — exactamente los mismos 2,140 candidatos A/B, contingencia completa y escenario spread 1.60 agregado; **PAPER research only**.

Test suites nuevos: `tests/infrastructure/test_vt31_ict_cleanroom_{cognition,cognitive_telemetry,single_trader,m1_execution,ops,order_lifecycle,cog_revocation_forensics}.py` y `test_vt31_fixed_spread_quote_scenario.py`. Último fast CI 35 passed. No inferir que la suite global de QORE en `main` esté verde sólo porque el fast suite aislado pase.

## 7. Sensor cognitivo: qué se ha probado y qué NO

Cognitiva procesó 1,059,784 M1 reales y produjo **137,160** evaluaciones de fuente con **62,885 decisiones válidas repetidas en M1** (no independientes entradas/órdenes). La instrumentación verifica input y output para M15, H1, H4, pools NY cash/Asia/London, barridos, desplazamiento MSS, tesis continuada, DOL, abstención final y acoplamiento real con OPS. **H4 se observa, pero actualmente no filtra ninguna entrada: 0 contribuciones a gate.** No atribuirle impacto inexistente.

La persistencia temporal **SÍ se usa**: de 2,140 ofertas source, **896** tenían MSS nuevo confirmado en la M1 de FVG y **1,244** venían de MSS original confirmado en M1 anterior y revalidado hasta el FVG posterior (London 303/463; NY AM 293/428; NY PM 300/353). Esto demuestra traza operativa, no edge estadístico.

**P0 CORREGIDO**: 937 fuentes pendientes inválidas antes de fix / 7,648 M1 observaciones repetidas → **0 / 0 tras OPS fix**, exacto replay 3Y verificado. Sin pruebas de order ACK real. Necesidad posterior: ablaciones verdaderas de componentes contra mismos datos **sólo después de definir método y ejecución**, no indicadores añadidos sin control.

## 8. El embudo de ofertas: por qué 2,140 NO son trades

De **2,286** ventanas completas del ICT Silver Bullet, **2,140** (London 766 / NY AM 721 / NY PM 653) encuentran primer FVG research candidato: ~94% de horas. Esta **alta permisividad** puede indicar que el detector MSS/FVG no captura suficiente fidelidad al concepto original; no es una tasa de trading. Cada FVG se propone sólo una vez por ventana, no hay entrada de broker.

Último OPS source ledger [#38018602495](https://github.com/mezas3238-hue/qore-core/actions/runs/38018602495):
- **2,076** ofertas resultan `SOURCE_INVALIDATED` al final de su hora;
- **46** `AMBIGUOUS_PRICE_PATH`;
- **17** `WINDOW_EXPIRED`;
- **1** `RESEARCH_TOUCH_NOT_FILL`.
- De las 2,076 cancelaciones: **1,587** `COGNITIVE_THESIS_REVOKED_OR_UNAVAILABLE` y **489** `CAUSAL_DOL_DIRECTION_OR_TARGET_CHANGED`. Estas causas OPS son excluyentes.
- **301** solapamientos CE M1 mientras elegible, SIN quote/ACK/fill. **737** solapamientos CE/cancelación EN MISMA M1 sin secuencia subminuto, **indeterminados**, no pérdidas ni fills. No contar CE después de cancelación.
- El dato **2,076/2,140 ≈ 97.0% source invalidations** NO autoriza la frase “97% de trades invalidados ANTES DEL FILL”. No conocemos momento de fill broker; COG decisiones llegan al cierre M1 y no resuelven recorrido intraminuto.

## 9. Investigación de causas: verdad de ejecución M1

[Forensic real 3Y #38020203387 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38020203387) etiquetó en el momento de revocación:
- **1,645** banderas de regreso del cierre M1 más allá del pivote roto M1 anterior;
- **1,019** banderas de MSS M1 contrario;
- **57** banderas de barrido del DOL seleccionado en esa misma M1;
- **698** revocaciones tienen simultáneamente 2+ banderas. **No sumarlas como causalidad independiente**.
- **62,075** reevaluaciones M1 tenían tesis activa anterior, **75,085** no tenían; 12,752 banderas por cierre que cruza pivote en reevaluaciones, 7,600 MSS opuestos, 333 DOL barridos (conteos repetidos M1, no trades).
- **198** instantes de tesis previa potencialmente válida donde un nuevo MSS no pudo seleccionar el objetivo nuevo, requieren revisión de precedencia/doctrina, no reactivar de forma retrospectiva.

**Hipótesis fundamentada**: el pivote roto por un MSS LONG (prior high) puede volver a cruzarse durante el retorno hacia el FVG **sin haber invalidado necesariamente el swing low opuesto protegido**. Asimismo en SHORT. El algoritmo B prueba una elección causal explícita de swing contrario, pero **no prueba que ICT ordene “pivote de 3 M1”**.

## 10. A/B pareado y preregistrado: base del juicio científico

A original = `VT31Trader` actual con COG/OPS como fuente. B experimental = **MISMO primer FVG M1, MISMO CE, mismo target DOL y reloj**, pero regla de invalidación usa último pivote contrario de 3 M1 confirmado ANTES del MSS inicial. MSS contrario exige ruptura nativa/desplazamiento y luego PRIMER FVG contrario confirmado en la misma ventana activa, **mismo o posterior M1**; 122 primer FVG contrarios de misma M1 del MSS y 562 posteriores; **684** eventos observados de secuencia. Las condiciones B de FVG cierre pleno, target previo a CE, expiración y `UNKNOWN` son formalizaciones ALG/QORE, NO necesariamente reglas explícitas ICT.

Preregistro fuente **antes de resultados**, [commit `d4db56fb45228d74a065349a97e562f2fbc6f657`](https://github.com/mezas3238-hue/qore-core/commit/d4db56fb45228d74a065349a97e562f2fbc6f657):
1. **Endpoint primario ÚNICO**: ventaja neta pareada B−A de **≥+5.0 puntos porcentuales** en primeros contactos CE M1 **no ambiguos** sobre los 2,140 candidatos.
2. **Guardia simultánea obligatoria**: **≤10%** candidatos B indeterminados. Si cualquiera falla → B NO promueve a producción.
3. Ventanas individuales descriptivas exploratorias, ajuste predefinido de tres comparaciones si se hacen inferencias, Bonferroni `alpha=0.05/3`; días repetidos necesitan técnicas por cluster, no fingir observaciones IID.

[Replay #38040127136 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38040127136), artefacto 11664804507, 29 pytest y stream 3Y. Resultados exactos:
- A `VALID_CE` **301**, B `VALID_CE` **789**; B-only **496**, A-only **8**, ambos 293; ganancia neta +488 / +22.803738pp.
- A indeterminado **637 / 29.77%**. B indeterminado **670 / 31.308411%** (619 por colisión CE/invalidación/target en misma M1; 51 geometría de swing contrario no utilizable).
- B invalidación **512**, target-before-CE **111**, expiración **58**. A invalidación **1,132**, target-before-CE **53**, expiración **17**.
- London A 115 / B 263, NY AM A 110 / B 282, NY PM A 76 / B 244; B desconocidos London 237/766, NY AM 223/721, NY PM 210/653.
- Contrafactual B-only 496 contactos CE M1 **(no fills)**: precio posterior dentro de la hora alcanzó wick del stop experimental primero **340**, tocó target DOL primero **32**, sin resolver antes del cierre hora **124**. Estos 340/32/124 son **condiciones de precio**, NO operaciones perdidas/ganadas ni win rate; el mercado puede tocar otros extremos antes de CE dentro de la misma vela.
- **GATE PRECOMPROMETIDO: FALLIDO** por 31.31% > 10%, aunque se supera +5pp. No variar el umbral después de mirar resultados. No promover B ni elegir London/NY ganadora por hindsight.

## 11. Ensayo adicional solicitado por propietario: BASE BID/ASK 1.60 — NO histórico de ticks

La captura muestra **NDX100 BID 30853.00 / ASK 30854.60**. La base aplicada a 3Y fue **spread fijo 1.60 puntos**, usando OHLC M1 NAS100 como supuesto MID `bid=mid−0.80`, `ask=mid+0.80`. Dirección correcta: LONG límite demanda `Ask ≤ CE`, SHORT límite oferta `Bid ≥ CE`. Prueba del **primer CE M1 original no ambiguo**, NO reconstrucción de ticks futuros ni estrategia de reentrada.

[CI #38257774657 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38257774657), 35 tests, artifact **11750991244**, código `90deb73a47cbc09b88580595800607f2516323b7`, 2,140 fuentes idénticas, histórico SHA confirmado.

| Ventana | FVG fuente | A OHLC-CE | **A compatible spread 1.60** | B OHLC-CE | **B compatible spread 1.60** | B-only compatible | A-only compatible |
|---|---:|---:|---:|---:|---:|---:|---:|
| London | 766 | 115 | **77** | 263 | **165** | 102 | 14 |
| NY AM | 721 | 110 | **97** | 282 | **231** | 142 | 8 |
| NY PM | 653 | 76 | **58** | 244 | **181** | 128 | 5 |
| **TOTAL** | **2140** | **301** | **232** | **789** | **577** | **372** | **27** |

**Diferencia pareada neta** `(372−27)/2140 = +16.1215pp`. Es mayor número de **solapamientos de precio** compatibles con Ask/Bid artificiales, NO ventaja de rentabilidad. **Indeterminados B 670 (31.31%) siguen intactos**, no pasan el preregistro. 0 fills comprobados; PF, DD, Sharpe, Sortino, net expectancy siguen **NO COMPUTABLES**.

**Advertencia de riesgo:** Un spread de un solo instante **no describe 2023–2026**; no mezclar NDX100 broker MT5 y NAS100 histórico sin verificación, y no inventar equivalencia de cuentas, moneda, fees, point value o tick_size. Interpretación correcta: análisis de sensibilidad que el propietario pidió y que está completamente ejecutado.

## 12. Problemas concretos pendientes — orden y responsables

### BLOQUEANTES P0 de ciencia y economía (antes de certificar)

**P0-A — EDGE DESCONOCIDO: NO EXISTE LISTA DE TRADES BROKER-EJECUTABLES.** No contamos con serie BID/ASK intraminuto del mismo símbolo/corredor para un periodo representativo, broker ACK, órdenes efectivas, cronología stop/target, comisiones aplicables, slippage o lote oficial. Los 2,140 candidatos son FVG de investigación, no 2,140 fills. Sin esto no se puede afirmar PF≥valor, drawdown, beneficio neto ni certificación. **Owner OPS**: datos/OMS; **Owner COG**: source-lineage, reglas as-of. **Cierre:** datos del mismo broker/contrato con timestampping y conciliación de source→offer→quote→ACK→position→close, pruebas de no-lookahead y tasas de cobertura reportadas; si no existen ticks suficientes, declarar `INSUFICIENTE_EVIDENCIA_POR_DATOS` y no “ganador”.

**P0-B — METODOLOGÍA SILVER BULLET NO FIELMENTE ACREDITADA.** MSS/pivote 3 M1, desplazamiento mediana×1.25, source FVG 94% de ventanas, target DOL y stop protegido son QORE research y podrían sobrepermitir setups o revocar entradas en retroceso natural. **Cierre:** tabla de doctrina con citas directas del ICT 2023, instante observable, componente, comportamiento actual, discrepancia, resolución predefinida, tests adversariales y peer-review ARCH1+ARCH2; no optimizar por PnL histórico.

**P0-C — RESULTADO A/B B FAILED 31.31% UNKNOWN.** **619** casos con CE + salida del setup en misma M1 con cronología desconocida y **51** con geometría de pivote opuesto no demostrable. Con spread fijo 1.60 siguen indeterminados. **No clasificarlos como fills, pérdidas ni “éxitos recuperados”.** **Cierre:** ticks mismo instrumento con timestamps sub-M1 y fuente confiable para resolver, o bandas conservadoras de escenarios mejor/peor y abstención; mantener 10% de preregistro intacto para B. No prometer que 619 se resuelven sólo por tener BID/ASK instantáneo.

**P0-D — CONTRATO NDX100 (MT5) vs NAS100 (fuente) SIN RECONCILIAR.** Captura NDX, datos NAS. Requiere broker/server, `symbol_info` (digits, point, trade_tick_size/value, trade_contract_size, calc_mode, min/max/step lots, stop/freeze, swap, trade sessions), moneda y broker price basis, tz server/Nueva York, mapping y feed-provenance. El ejemplo 0.01 lot/pérdida −0.45 es sólo muestra. **Cierre:** contrato oficial trazable + comparación de puntos/timestamps con fuente, sin metadatos secretos en GitHub.

**P0-E — MOTOR ECONÓMICO, BROKER SAFE Y PORTAFOLIO NO INTEGRADOS.** `SourceLimitOrderAudit` es monitor de research, `ExternalExecutionAck` es DTO, no MT5 router/verdadero ticket reconciliado. Falta evidencia de cancelación, ACK tarde, fills parciales, rechazo/requote/slippage y stop/target, lotaje y gestión conjunta con CIBO/Shared. **Cierre:** PAPER aislado con evento `ExternalExecutionAck` auténtico, reconciliación secuencia y posiciones de UNA VT31 con riesgo de cartera; NO LIVE antes de compuertas formales QORE.

### P1 de calidad metodológica e infraestructura

1. **OHLC histórico no sabemos si es BID, MID, ASK**: actual spread sim asumió MID por investigación, no prueba. Sensibilidad fija 1.60 no reemplaza spread histórico variable ni eventos high-vol.
2. **Secuencia intrabar y censura:** revisar código del A/B por primer CE “limpio”, cancelación M1 simultánea, `SOURCE_INVALIDATED` vs `TARGET_BEFORE_CE`, 737 casos originales ambiguos y 619 B; asegurar que último cierre M1 no retrocancela un quote anterior sin ACK. Corregir TODO bug metodológico antes de evaluación económica; no usar stop-touch de 340 casos como pérdidas.
3. **Pivote protegido B / precedencia:** las causas B de cierre del swing protegido fueron cero en su categoría terminal frente a otras salidas: puede ser censura por CE temprano o geometría; auditar sin modificar tres-bar swing por resultados. Revalidar stop respecto al origen de desplazamiento, FVG y doctrina primary ICT.
4. **MSS contrario:** usar el **mismo motor causal desplazamiento** en direcciones opuestas; primer FVG opuesto después MSS dentro MISMA ventana (122 mismo M1, 562 M1 posterior), garantizar no FVG posterior al cierre ni repetición elegida hindsight. Documentado como formalización ALG, no ICT explícito.
5. **DOL hierarchy insuficiente:** NY cash previo no equivale a 24 h PDH, fuentes Asia/London deben formar intervalos completos sin staleness/sweeps falsos. Investigar highs/lows anteriores reales, swing semanal, implicaciones de días festivos con source exacta, no introducir HTF futuro. H4 sensor observado pero **no entry gate**.
6. **Fuente/permisividad:** 2,140 primeros FVG / 2,286 source hours ≈94% indica posibles falsas condiciones MSS. Revisar criterio de relevancia no por maximizar señales ni “filtro de confluencias” inventado.
7. **Falta causal ablation económica:** llamar a sensor ≠ razonamiento independiente ≠ valor marginal. Ablación de compuertas/rol de COG sólo tras resolver política y datos ejecutables.
8. **`quote_tick_science.py` sin cualificación:** no está integrado al CI de spread 35 tests como motor de datasets reales. Exigir tests invalid/duplicate-millisecond, quote order, wrong symbol, gaps, timestamp format, SHA y pruebas de integridad antes de asignarle autoridad.
9. **CIBO / VPS / repos:** VPS `vps-vrix` figuró OFFLINE en revisión anterior; comprobar estado ACTUAL con acceso autorizado, no decir que sigue offline sin reconfirmar. Conexión externa no equivale a permiso de trading, solo read-only si usuario autorizó.
10. **PRs stacked y global CI:** evitar doble merge de COG #751; revisión coordinada #750/#752/#753/#833. El fast CI verde es sólo contrato local; QORE global tests/strict mypy y CSP/habilidades deben verificarse a SHA objetivo antes de integración.

### P2 (DESPUÉS de edge)

Integración cognitiva extra, H4 como filtro, optimizaciones de ejecución, nuevas variantes y adaptación multi-índice requieren evidencia previa. Por ahora CONGELAR ampliación de arquitectura de VT31; no replicar esto automáticamente en 33 mercados ni abrir nuevos horizontes.

## 13. Plan exacto para el siguiente arquitecto (sin improvisar)

**Paso 1 — Recuperar y congelar custodia (primera tarea).**
Leer ESTE handoff, docs fuente enumerados al final, Issue #727, PRs #750/#751/#752/#753/#833; extraer SHA de cada HEAD, revisar que ninguna rama/pr merge haya cambiado, y verificar artefactos CI con hashes. Ejecutar full M1 source 3Y y confirmar 1,059,784 / 137,160 / 2,140, 0 P0 pending-without-cog, 35 tests de fixed spread. Registrar cualquier discrepancia ANTES de nuevas reglas.

**Paso 2 — Definir por escrito exactamente qué entra y qué invalida.**
Crear `VT31_ORIGINAL_ICT_DOCTRINE_AND_FORMALIZATIONS` con fuente primaria, min 1M1 swing, MSS/desplazamiento, objetivo DOL, tres-bar FVG, retrace CE, protected opposite swing, full FVG mitigation, opposite MSS+first FVG, expiración. Separar `EXPLICIT_2023_ICT`, `QORE_ALG_FORMALIZATION`, `EXPERIMENTAL_B`. A/B actuales NO son autorización para reemplazar A por B. Revisar cuál micro-pivote es SWING ROTO vs SWING OPUESTO, con eventos testables.

**Paso 3 — Obtener y verificar datos, NO programar más filtros.**
OPS coordina acceso broker (MT5/cTrader cuando autorizado), histórico de ticks BID/ASK en UTC milisegundos, contrato de símbolo y equivalencia NAS100/NDX100, fechas de cobertura, puntos vacíos, spread por sesión, retención, comisiones, símbolos y offsets. Sólo fuentes reales firmadas/hash. Si el usuario proporciona sólo snapshot, repetir sensibilidad 1.60 ya completada, no declarar fill. No extraer credenciales ni adjuntar datos personales/account IDs al repo.

**Paso 4 — Reproducir trayectorias ambiguas con resolución temporal correcta.**
Estudio pareado de los **2,140 IDs**. Para cada uno log `as_of_M1`, first FVG, side/CE/target, source COG, MSS pivot orig/opuesto, oferta/tick quote (si disponible), invalidación y orden de acontecimientos. Primero auditar 619 B same-M1 ambiguos + 51 geometrías; conservar estado `INDETERMINATE` donde no haya prueba suficiente; clasificar `TARGET_BEFORE_CE` aparte de invalidez estructural. Guardar matriz A/B **pareada**, no sólo totales.

**Paso 5 — Fase de cribado económico, con criterio de STOP decidido ANTES de outcomes.**
Registrar control negativo y supuesto BID/ASK conservador; al disponer de quote/execution facts, simular PAPER broker-neutral con **ACK real/externo para declarar real fill**, o `SIMULATED_EXECUTION` expresamente etiquetado si se modela con supuestos, jamás mezclar. Medir trades confirmados, densidad/año, gross/net expectancy, PF net, max chronological DD en R y dinero, Sharpe, Sortino, MFE/MAE, frecuencia de pérdidas consecutivas, stopped target overlap y cuenta de cartera de una VT31. Interés especial London vs NY AM vs NY PM y regímenes/volatilidad; respetar el ajuste múltiple. Sin fuente ejecutable suficiente, dar dictamen `DATOS_INSUFICIENTES`, no ciencia falsa.

**Paso 6 — Pruebas de robustez, antes de tocar Fresh Holdout.**
Sobre development only, usar variación PREDECLARADA spread real por rango/session o escenarios razonables y costes alternativos sin calibrar ganadores. Intervalos por cluster de día/semana, bloque bootstrap, sensibilidad del MT5 NDX vs histórico NAS; walk-forward/temporal holdout sólo con protocolo aprobado. No decidir luego de ver un subconjunto ganador de horas. Si gate P0 económico pasa y OPS/COG acuerdan una especificación CONGELADA, ejecutar certificado de holdout sellado una sola vez bajo política de datos/autoridad.

**Paso 7 — Dictamen de existencia de VT31.**
`CONTINUAR` exclusivamente con net edge y DD tolerable, método documentado, fuente equivalente, cobertura adecuada y resultados independientes; `RETIRAR` si prueba de desarrollo suficientemente fuerte rechaza el edge o las condiciones operativas lo hacen inviable; `DATOS_INSUFICIENTES` si falta fuente de ejecución, con lista cerrada y fecha de vencimiento de investigación (establecer con propietario). **No emplear número alto de FVG como argumento para seguir ilimitadamente**.

## 14. Gates de cierre (todas verificables; NO inventar valores oficiales Core)

| Gate | Criterio observable | Estado |
|---|---|---|
| G0 Custodia cleanroom | ONE VT31, no legacy, 3 NY source windows M1 DST correctos | **PASÓ en research** |
| G1 Causalidad | fuente SHA, sin M1 futuro, compleción HTF/liquidez as-of, sensor COG/OPS 1:1 | **PASÓ en research** |
| G2 P0 integridad source | 0 pending sin COG; no same-direction auto-MSS revocation no fundada | **PASÓ en replay 3Y OPS** |
| G3 Fidelidad ICT | artículos primarios y jerarquías MSS/FVG/retorno/stop aceptados por dos arquitectos | **ABIERTA** |
| G4 A/B fuente prereg | B net +5pp CE Y ≤10% indeterminado | **FALLÓ** (31.31% desconocidos) |
| G5 BID/ASK contrato | fuente histórica mismo símbolo/broker y lado quote, cobertura y DST verificados | **ABIERTA** |
| G6 OMS/ACK | quote crossing no fill, confirmación broker, cancel race, no reabrir estado tras invalidación | **ABIERTA** |
| G7 Económico | net expectancy>0, PF/Sharpe/Sortino/DD, trades, fees, sizing y límites Core **consultados a sus contratos oficiales** | **NO CALCULABLE / NO PASADO** |
| G8 Robustez | ventana, regímenes, walk-forward, multiplicidad, PnL out-of-sample, Monte Carlo | **NO PASADO** |
| G9 Holdout + riesgo | método congelado, Fresh Holdout aprobado + QDLE/CIBO exposure y VPS PAPER | **SELLADO / NO AUTORIZADO** |
| G10 LIVE | todos Gates oficiales QORE y autorización del propietario explícita | **PROHIBIDO** |

**No adivinar umbral exacto de PF, Sharpe, Sortino o DD para “Core certification”**; recuperar el fichero/contrato oficial vigente de QORE antes de reportar PASS. No afirmar que existe PF del cleanroom porque se hicieron tres años de source-only.

## 15. Comprobaciones reproducibles y enlaces de fuente para continuidad

- Coordinator OPS handoff: [VT31_CLEANROOM_3Y_JOINED_M1_OFFER_COG_REVOCATION_HANDOFF_2026-10-09.md](https://github.com/mezas3238-hue/qore-core/blob/84fdd75c345a40779a2e1c2bef2876ae5e7798a1/docs/research/VT31_CLEANROOM_3Y_JOINED_M1_OFFER_COG_REVOCATION_HANDOFF_2026-10-09.md)
- Auditoría sensores: [VT31_COG_COMPONENT_IO_3Y_AUDIT_2026-10-09.md](https://github.com/mezas3238-hue/qore-core/blob/952f6afd18600087cae8e8f32a70660584259c04/docs/research/VT31_COG_COMPONENT_IO_3Y_AUDIT_2026-10-09.md)
- Causas de revocación: [VT31_COG_REVOCATION_ROOT_CAUSES_REAL_3Y_2026-10-10.md](https://github.com/mezas3238-hue/qore-core/blob/03fb9f48620c598ae07c3f147eb55bdffa86d354/docs/research/VT31_COG_REVOCATION_ROOT_CAUSES_REAL_3Y_2026-10-10.md)
- Preregistro fuente A/B: [VT31_OPPOSITE_PIVOT_AB_PREREGISTRATION_2026-10-10.md](https://github.com/mezas3238-hue/qore-core/blob/949a4fdd335eb9943ea6436f6136415029aff599/docs/research/VT31_OPPOSITE_PIVOT_AB_PREREGISTRATION_2026-10-10.md), [commit antes de ensayo d4db56f](https://github.com/mezas3238-hue/qore-core/commit/d4db56fb45228d74a065349a97e562f2fbc6f657)
- Resultados pareados: [VT31_PAIRED_AB_SOURCE_REAL_3Y_RESULTS_2026-10-10.md](https://github.com/mezas3238-hue/qore-core/blob/949a4fdd335eb9943ea6436f6136415029aff599/docs/research/VT31_PAIRED_AB_SOURCE_REAL_3Y_RESULTS_2026-10-10.md), [CI #38040127136](https://github.com/mezas3238-hue/qore-core/actions/runs/38040127136), artifact 11664804507.
- Snapshot NDX100 bid/ask: [VT31_NDX100_LIVE_MT5_BID_ASK_SINGLE_SCREENSHOT_EVIDENCE_2026-10-12.md](https://github.com/mezas3238-hue/qore-core/blob/949a4fdd335eb9943ea6436f6136415029aff599/docs/research/VT31_NDX100_LIVE_MT5_BID_ASK_SINGLE_SCREENSHOT_EVIDENCE_2026-10-12.md).
- Resultados 1.60: [VT31_FIXED_SPREAD_1P60_USER_BIDASK_3Y_RESULTS_2026-10-12.md](https://github.com/mezas3238-hue/qore-core/blob/e51d1bc8a7d14514507d343875b273e07e9afa6a/docs/research/VT31_FIXED_SPREAD_1P60_USER_BIDASK_3Y_RESULTS_2026-10-12.md), [CI #38257774657](https://github.com/mezas3238-hue/qore-core/actions/runs/38257774657), artifact 11750991244.
- NDX100 0.01 lot real económico ejemplo: [VT31_NDX100_MT5_USER_SCREENSHOT_ECONOMICS_2026-10-10.md](https://github.com/mezas3238-hue/qore-core/blob/84fdd75c345a40779a2e1c2bef2876ae5e7798a1/docs/research/VT31_NDX100_MT5_USER_SCREENSHOT_ECONOMICS_2026-10-10.md).
- P0 source fix real 3Y: [CI #38018856150](https://github.com/mezas3238-hue/qore-core/actions/runs/38018856150), artifact 11657187430.
- OPS repaired offer ledger [CI #38018602495](https://github.com/mezas3238-hue/qore-core/actions/runs/38018602495), artifact 11657461650.
- Directo navegación: [Issue #727](https://github.com/mezas3238-hue/qore-core/issues/727), [PR #750](https://github.com/mezas3238-hue/qore-core/pull/750), [#751](https://github.com/mezas3238-hue/qore-core/pull/751), [#752](https://github.com/mezas3238-hue/qore-core/pull/752), [#753](https://github.com/mezas3238-hue/qore-core/pull/753), [#833](https://github.com/mezas3238-hue/qore-core/pull/833).

**Fast reproducible commands AFTER checkout of a pinned SHA and authorized artifact retrieval** (source file not checked into git, never substitute example OHLC for real data):
```bash
python -m pip install -e ".[dev]"
python -m pip install "ijson>=3.3,<4"
PYTHONPATH=src pytest -q -o addopts='' \
  tests/infrastructure/test_vt31_fixed_spread_quote_scenario.py \
  tests/infrastructure/test_vt31_ict_cleanroom_cognition.py \
  tests/infrastructure/test_vt31_ict_cleanroom_cognitive_telemetry.py \
  tests/infrastructure/test_vt31_ict_cleanroom_ops.py \
  tests/infrastructure/test_vt31_ict_cleanroom_order_lifecycle.py
# Run verified workflow:
# .github/workflows/vt31-fixed-spread-1p60-3y.yml
# Actual Actions 38257774657 will re-fetch immutable 3Y source from artifact
# 11459859004, enforce SHA256, and upload JSON+signatures.
```

## 16. Resumen para el siguiente arquitecto y primera comunicación al propietario

**Lo ya cerrado**: reconstrucción cleanroom de 1 VT31/M1/2 sesiones, desarrollo de COG, sensores de I/O, 3Y fuente comprobada, 2,140 primeras FVG research, revocación sin COG a 0, auditoría de causas, A/B preinscrito/pareado, escenario de spread 1.60 completado y datos enviados a Arquitecto OPS por GitHub.

**Lo que aún NO tenemos**: evidencia de origen ICT completamente auditada en stop/pivote/FVG, 3Y bid/ask de broker del mismo instrumento, broker fills, ACK/fees/lots contrato, PnL económico neto, PF/DD/Sharpe/Sortino, positividad robusta, QORE certificados, Fresh Holdout, autorización real. **No reemplazar con imaginación**.

**Orden vinculante**: (1) verificar custodia y código; (2) doctrina MSS/FVG/pivote; (3) datos del broker y símbolo; (4) reanalizar UNKNOWN y cronología; (5) cribado económico con stop/target/costes explícitos; (6) robustez/holdout condicionado; (7) continuar o retirar. Mantener colaboración Issue #727. **Detener expansión cognitiva hasta saber si hay edge.**

**Dictamen final del arquitecto saliente**: VT31 es un laboratorio de estructura algorítmica reproducible, pero **su modelo operativo aún no ha acreditado una ventaja económica auténtica**. Su continuidad debe ser una **última fase científica de tiempo y alcance limitado**, no una promesa de rentabilidad. Con evidencia desfavorable, recomendar retiro aunque el software sea técnicamente elegante.

---

**Fin del Handoff Maestro Integral — estado explícitamente sujeto a revisión si cualquier commit, cobertura de fuente o prueba cambia después del corte.**
