# VT31 — Dictamen económico urgente basado en datos ya disponibles (13 octubre 2026)

**DECISIÓN OPERATIVA: `NO_GO`.** No activar dinero real ni declarar edge neto. **DICTAMEN CIENTÍFICO sobre la V1 nueva: `NOT_IDENTIFIED`, no `PROVEN_UNPROFITABLE`.** El resultado direccional NEGATIVO preregistrado de la cohorte histórica es real en su propio alcance: [PR #874](https://github.com/mezas3238-hue/qore-core/pull/874) 2.140 señales OLD, gross 15min −1.919664 pts; coste hipotético fijo 1.60 → −3.519664 pts. No es la entrada LIMIT CE/stop C2 nueva.

Este informe es una **auditoría exploratoria posterior a solicitud explícita del propietario**, NO un preregistro, no parte de G3 firmado, no activación de V1 ni prueba confirmatoria de la economía ICT. No cambiar reglas o umbrales por su resultado. **Advertencia esencial: los 2.140 pertenecen a filtro LEGADO DOL−C3, NO a la nueva cohorte MSS-close.** No trasplantar estos trades o etiquetas a V1, no forzar un juicio de la nueva V1 con este histórico. 619 same-minute old B y 51 stops invalid B mantienen sus propias etiquetas; este ensayo no los reemplaza.

## Datos usados, integridad y fuentes

1. M1 original **1.059.784** barras descargadas del artifact [#11459859004](https://github.com/mezas3238-hue/qore-core/actions/runs/38018856150), miembro `NAS100/market-evidence.json` SHA256 **`0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa` VERIFICADO nuevamente byte-exact**. Archivo define `provider_symbol_name=USTEC`, `symbol.symbol_id=10014`, `symbol.symbol_name=NAS100`, cuenta cTrader DEMO; esto estrecha la identidad de fuente frente al catálogo native QORE, pero **no prueba condiciones monetarias de contrato, tarifa, matching engine ni ejecuciones**.
2. Ledger A/B OLD fuente sin fills [Actions artifact #11657461650](https://github.com/mezas3238-hue/qore-core/actions/runs/38018602495), miembro `vt31-ict-cleanroom-3y-m1-offer-ledger.json`: **2.140 fuentes**, 0 broker-execution ACK; contenía timestamps de C1, C3, CE, DOL y revocación de tesis.
3. USTEC BID/ASK cTrader DEMO, fuente independiente QORE Native #853 adaptada a horas Silver Bullet: piloto [#11801205225](https://github.com/mezas3238-hue/qore-core/actions/runs/38374757273/artifacts/11801205225) + wave2 corregida [#11801263502](https://github.com/mezas3238-hue/qore-core/actions/runs/38377233495/artifacts/11801263502). 30 horas reales, **483.103 ticks-side**, hash SHA de originales y listas individuales verificados, [informe de integridad](https://github.com/mezas3238-hue/qore-core/blob/291dfcafc6beb0a7cc72f75e4947b92611305767/docs/research/VT31_G5_REAL_USTEC_30H_BIDASK_AND_3Y_M1_CROSSSOURCE_RESULT_2026-10-13.md).

## A. Intersección de las 2.140 fuentes OLD con los 10 días de BID/ASK REAL

Cruce determinista por `NY day + named source session` en los 30 segmentos NY de una hora; timestamp posterior **estrictamente a formed_at** hasta el menor entre cierre ventana NY y `cognition_lost_or_source_invalidated_at` archivado, sin imputar data cuando no corresponde. LONG: ASK histórico observado <= CE; SHORT: BID histórico observado >= CE. La cotización puede coincidir con CE pero **NO prueba fill LIMIT** o que la orden siquiera existiera en servidor.

- **10** FVG de cohorte OLD en los 30 segmentos.
- **4/10** tuvieron cruce BID/ASK as-of antes de terminar su estado pendiente old; todos fueron de la sesión Londres.
- **6/10** no tuvieron ese cruce.
- **3/4** de los cruces se produjeron durante la **última M1 antes del registro de revocación**. Hay que mantener cronología exacta de orden/cancel/ACK; aunque tick temporal preceda al cierre de M1, precio tocado no certifica matching.
- **0/10 broker execution ACK aportados**.

**Dictamen A:** `SOURCE_QUOTE_CE_CROSS_OBSERVED_4_NOT_FILL`, muestra 10 fuentes OLD, **NO nueva V1**, insuficiente para cualquier PF verdadero.

## B. Shadow mecánico 3Y para identificar si con M1 se puede adjudicar economía

Escenario exploratorio **NO preregistrado ni broker-authenticado** de C2 wick ±0.01 index point asumido como grid para geometría, CE pendiente sólo DESPUÉS de C3, revocación de fuente OLD como cancelación M1-close, TP DOL y salida por precio M1 BID a 15:55 NY, sin parciales. El histórico M1 se verificó BID-aligned para muestra 30h, pero los ASK históricos fuera de esos 30h no existen. Se impusieron escenarios ASK=BID+`s`, con `s` fijo arbitrario `0, 0.8, 1.6, 2.4` puntos; no es coste oficial ni registro auténtico. El mismo minuto de entrada/stop/TP o revocación se marca UNKNOWN, no clasificado ganancia/pérdida; también los gaps. **R y PF de la fracción resuelta no sirven como estimadores de la población al excluir estos casos selectivamente.**

| Escenario spread supuesto | OLD 2.140 | No entrada aparente | UNKNOWN entrada/cancel misma M1 | UNKNOWN entrada/salida misma M1 | Resueltos en escenario (sesgo de selección) |
|---|---:|---:|---:|---:|---:|
| 0.0 | 2.140 | 1.199 | 593 | 29 | 316 |
| 0.8 | 2.140 | 1.240 | 589 | 44 | 264 |
| 1.6 | 2.140 | 1.289 | 568 | 65 | 216 |
| 2.4 | 2.140 | 1.320 | 542 | 85 | 191 |

Diferencias menores restantes: 2 casos geometry inválida en cada escenario; en `s=0` y `s=0.8`, 1 salida horaria sin M1 completa. **Al menos 568** eventos (y hasta 593) tienen carrera pendiente/cancel indeterminada aun tras elegir spread fijo. El volumen de UNKNOWN no es aleatorio; **descartar los casos y publicar PF/expectancy como verdadero sería sesgo de supervivencia**.

En el escenario `s=0.8` (ilustrativo solamente): 235 stops, 21 targets DOL y 8 time exits resueltos, 264 desenlaces sobre 2.140 fuentes. Cualquier PF condicional a estos 264 outcomes omite **589** conflictos simultáneos, **44** entrada/salida mismo minuto y **1.240** aparentemente no ejecutados, bajo supuestos BID+spread no autenticados. Ni a favor ni en contra del edge V1.

**Separación causal adicional:** la política OLD de invalidación y los candidatos OLD no son la política G3; las geometrías C2 calculadas aquí fueron tomadas como hipótesis shadow no implementadas, sin tick oficial, sin fees, swaps, órdenes o ACK, ni precios de salida ASK auténticos. No existe motivo válido para publicar `V1_PF` o `V1_DD` a partir de esto.

## C. Dictamen de parada para decisión inmediata

- **`OPERATION_NO_GO`** para VT31 y CIBO: la señal direccional de la fuente antigua falló y no hay evidencia neta auditada de la nueva V1.
- **`V1_ECONOMIC_EDGE_NOT_IDENTIFIED`**: no significa falsación de toda entrada CE. La muestra 30h prueba disponibilidad de source, pero solo 10 señales OLD cruzan la muestra, 4 cotizan en CE y 0 prueban ACK.
- **No pedir más hiperoptimizaciones.** Para un dictamen YES/NO económico de la V1 se requiere: congelamiento legítimo de su acta+code, reconstruir cohorte nueva completa con MSS as-of, recolección real BID/ASK en TODOS los intervalos de órdenes y toda la vida posterior de posiciones hasta TP/SL/15:55 (no solo 03–04/10–11/14–15), contrato USD/valor de tick/lote y tarifas históricas, simulador PAPER que no llama fill a una touch, análisis de UNKNOWN, bootstrap por semana y posterior fresh holdout.
- Si no se financia/dispone de todo ello, **decisión comercial es detener VT31** y no habilitar nuevas horas de descargador a ciegas. Los costes de mantener un trader no demostrado no se justifican sólo por indicadores o simulación OHLC.
- **Sin cambios** al G3 r1.3 doc SHA `a446afa17ed6e411b8f0b6fc182b103a78959a97` y código SHA `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`, se mantienen `G3_PENDING_DUAL_SIGNATURE`, HOLDOUT/PROD/LIVE bloqueados.

**Conclusión obligatoria para el propietario:** hoy NO hay prueba de que VT31 sea rentable; no hay base cuantitativa para activarlo. Declarar `rentable` o `sin edge imposible` en forma absoluta sería evidencia fabricada.
