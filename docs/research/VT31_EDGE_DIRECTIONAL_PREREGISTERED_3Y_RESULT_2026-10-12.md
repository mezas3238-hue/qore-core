# VT31 — Dictamen científico: screening DIRECCIONAL preregistrado 3Y NAS100 M1

**12 octubre 2026. Arquitecto OPS. Prueba NUEVA y limitada para la pregunta del propietario “¿VT31 tiene edge real?”**

## Dictamen de esta fase

**PRE-REGISTERED 15-MIN DIRECTIONAL SCREEN: FAIL.**  
**EDGE ECONÓMICO VERDADERO DEL ICT SILVER BULLET CON ENTRADA CE: NO DEMOSTRADO.**  
**No autorizar LIVE, no certificar, no contar los 2.140 candidatos como trades.**

Se debe abandonar la idea de que los 2.140 FVG o la mejora source-only B son evidencia de edge. Una prueba congelada ANTES de ejecutar el resultado evaluó si las direcciones del propio algoritmo predicen movimientos futuros en el mercado. Dio un retorno hipotético medio **NEGATIVO en cada una de las cuatro ventanas temporales estudiadas**, con el horizonte primario de 15 minutos claramente adverso. Esta es evidencia empírica negativa **específica**: NO autoriza declarar matemáticamente que ninguna entrada de retroceso CE, salida por DOL ni gestión ICT pueda funcionar. La señal en el cierre del FVG no parece presentar ventaja por sí sola.

## Procedencia reproducible y preregistro

- **Preregistro publicado ANTES de leer resultados:** `docs/research/VT31_PREREG_EDGE_DIRECTIONAL_3Y_M1_2026-10-12.md`, primer commit de la rama `agent/vt31-edge-directional-preregistered-20261012`. No se cambiaron hipótesis después.
- **Runner:** `scripts/vt31_edge_directional_15m_preregistered_3y_v1.py`, fuente de trading limpia usada sólo para seleccionar señales, no mutada.
- **[CI GitHub Actions 38310949637 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38310949637)**, commit runner+workflow `0ff8ae437efd882bd41c0da5058c5e23dfab69a0`.
- **Artifact nuevo:** `11774781034`, `vt31-directional-15m-prereg-3y.json`, identifica SHA256 tanto del ledger de candidatos como del M1 original. Prueba read-only independiente de **los cuatro horizontes**: [GitHub Actions 38311120068 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38311120068). No recalibración ni rerun escogido por resultados.
- Eventos previos FIJOS: `2.140` primeros FVG source-only, archivo original de OPS `11657461650` de 38018602495, 766 Londres/721 NY AM/653 NY PM. 1,059,784 M1 congeladas de GitHub artifact `11459859004`, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`. **Cobertura de timestamps M1 exactos para h=15: 100 % (2.140 / 2.140)**. Mismo trader, M1, tres ventanas New York / DST, ningún dato del Fresh Holdout nuevo.
- Los eventos SON M1 causales formados al cierre de tercera vela. El test usa `M1_open(t)` en el minuto inmediato siguiente y `M1_open(t+h)` en horizonte fijo. Si falta alguna M1 intermedia se excluiría como missing, no se rellena; 100 % exacto en los 4 horizontes en esta fuente.
- **No es el plan operativo ICT por orden LIMIT al 50% del FVG**. Prueba de forecast de precio a partir de la señal; no hay fills en CE/SL/TP. No se agregaron stop, take profit, parciales, lotaje ni decisión cognitiva posterior a la entrada.
- **Spread sintético fijo 1.60 puntos de imagen de usuario NDX100:** histórico NAS100 OHLC SUPUESTO MID (sin validación), ASK hipotético = MID+0.80 para buys y BID hipotético = MID-0.80 para sells, de entrada y salida: `net_pts=side×(future_open−entry_open)−1.60`. No verdadero spread histórico, cuenta/comisiones verificadas ni instrumento equivalente NDX100. Un número `net` aquí NO equivale a beneficio real.

## Resultados 3 años — todos los 2.140 candidatos, sin filtrar ganadores

| Horizonte tras confirmación FVG | Papel | N completo | Media GROSS dirección (pts) | Media después de coste hipotético 1.60 (pts) |
|---|---|---:|---:|---:|
| 5 min | Exploratorio | 2,140 | **−0.267794** | **−1.867794** |
| **15 min** | **PRIMARIO PREFIJADO** | **2,140** | **−1.919664** | **−3.519664** |
| 30 min | Exploratorio | 2,140 | **−2.264743** | **−3.864743** |
| 60 min | Exploratorio | 2,140 | **−1.390893** | **−2.990893** |

### Resultado principal de inferencia SIN seleccionar horizonte

- **M1 cobertura exacta:** 100 %.
- **Media gross 15 min −1.919664 pts**; después del coste SIMULADO de 1.60 => **−3.519664 pts**, mediana neta **−3.000000** pts.
- **Bootstrap por bloques ISO semanales (157 semanas, 5,000 remuestreos, semilla 10122026): IC 95% de la media neta [−5.130648, −2.019817] pts**.
- **Control unilateral con inversión aleatoria de signos por semana** (5,000 réplicas; semilla 31102026): p de efecto DIRECCIONAL BRUTO positivo **0.99280144**. No evidencia de dirección favorable; este p alto NO demuestra automáticamente el edge de invertir todas las entradas.
- **Fracción de movimientos netos hipotéticos positivos a 15m: 0.435981**; esto NO es tasa de aciertos de trades.

### Tres ventanas (15m primario)

| Sesión de fuente ICT | N | Media gross 15m (pts) | Media neta hipotética 15m (pts) |
|---|---:|---:|---:|
| Londres | 766 | −0.766789 | **−2.366789** |
| NY AM | 721 | −4.126768 | **−5.726768** |
| NY PM | 653 | −0.835100 | **−2.435100** |
| **Total** | **2,140** | **−1.919664** | **−3.519664** |

No escoger retrospectivamente ventana/horizonte con menos pérdida. Los 5/30/60 son descriptivos, NO pruebas múltiples para aprobación. Todos los retornos netos son negativos. A 60m, NY PM gross +0.168407, pero net hipotética **−1.431593**: no fingir ventaja rentable a partir de ese subtotal.

## Qué prueba y qué NO

**Prueba:**
- En fuente de desarrollo histórica, las direcciones M1 que Vt31 emite al primer FVG apropiado NO proporcionan ventaja a mercado en horizonte prefijado de 15m. Están, de hecho, orientadas contra el movimiento neto posterior bajo esta definición.
- No hay justificación empírica para declarar edge a partir de 2,140 FVG, del mayor número de coincidencias de CE en B, de Fast Runner verde ni de 35 tests exitosos de spreads.
- El estudio se diseñó sin reasignar población por PnL, sin reoptimizar parámetros y sin ver los 2,140 outcomes antes del preregistro.

**No prueba:**
- Que el modelo exacto ICT con retorno *LIMIT al CE* y SL/TP líquido no tenga edge: esa ejecución podría seleccionar precios o trades diferentes. Tampoco certifica que lo tenga. El indicador actual sigue sujeto a excesiva densidad (2,140/2,286 ventanas ≈94%), lo cual requiere auditar su fidelidad.
- Que exista un edge rentable EN SENTIDO CONTRARIO: no se preregistró estrategia contraria, ni tenemos broker fills; invertir direcciones a posteriori sería sobreajuste.
- Que 15m sea la salida "correcta" de ICT. No se trasladaron objetivos DOL, timing de orden, stops, pérdida por invalidez ni comisiones reales.
- Que esta investigación es OOS independiente: el 3Y fue investigado antes por los arquitectos; el preregistro solo precede esta *nueva prueba estadística*, no a la selección previa de metodología.
- Que el proxy MID NAS100 ↔ NDX100 MT5 es contractual o histórico. Un snapshot de spread 1.6 no lo demuestra.

## Acción P0 — criterio de continuación cerrado

1. **Congelar COG, filtros y nueva búsqueda de PF.** No arreglar el −3.52 cambiando a posteriori la ventana, dirección, displacement o target. Investigar fidelidad de fuente ICT sólo con enseñanza primaria.
2. **Una única fase económica decisiva** si se consigue archivo NAS100/NDX100 realmente equivalente de BID/ASK ticks históricos con UTC, condiciones de contrato/moneda/lote, spreads/fees y latencias. Simular **estrictamente modelo Silver Bullet CE limit**, señales originales frozen, cancelación/ACK, stops/targets y fills con orden de eventos; evaluar cuenta de un VT31 London+NY. Reportar PF/DD/expectancy/riesgo/OOS solo cuando sean reales o transparentemente paper con ejecución modelada y cobertura comprobada.
3. Si no hay fuente de ticks históricamente equivalente, **cerrar por DATOS INSUFICIENTES PARA DEMOSTRAR EDGE ECONÓMICO** en vez de reclamar rentabilidad. Definir plazo de investigación con propietario; evitar exploración indefinida.
4. Si ensayo CE REAL demuestra resultado negativo robusto bajo especificación congelada, recomendar **RETIRAR VT31**; si demuestra net edge positivo, replicable y Core gates, considerar continuar sin adelantar LIVE.

**Decisión ACTUAL:** `NO_EVIDENCIA_PREDICTIVA_NETA_EN_SCREENING_15M` + `EDGE_ECONOMICO_NO_DEMOSTRADO`. No certificar, no LIVE, no cambiar producción. Se ha aportado evidencia adversa nueva real sobre 3 años.
