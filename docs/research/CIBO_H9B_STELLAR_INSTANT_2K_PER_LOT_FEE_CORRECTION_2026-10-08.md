# CIBO H9b — CORRECCIÓN CANÓNICA DE COMISIONES: Stellar Instant USD2k
**08-10-2026 | Research only | CIBO NO CERTIFICADO | CORRECCIÓN DE H9**

**IMPORTANTE:** El informe original H9 y sus ocho resultados asumían un cobro *incorrecto* de USD7 fijo por entrada. **Quedan sustituidos** como evidencia de la hipótesis tarifaria del usuario. Se corrigió el replay local y se ejecutaron **12 pruebas cronológicas de 3.368 señales fuente** sin atribuir resultados futuros antes de liquidar.

## Dos lecturas de los ejemplos del usuario y resolución matemática

La instrucción principal es USD7 **por lote a la apertura** + USD7 **por lote al cierre**, **USD14 por lote por operación ida/vuelta**. Fórmula: `FEE_ROUNDTRIP_USD = abs(lots)*14`, debitando `7*lots` a la apertura y `7*lots` al cierre. Se reserva previamente la parte de cierre al calcular riesgo disponible.

| Lotes | Open USD | Close USD | Total USD |
|---:|---:|---:|---:|
| 0,01 | 0,07 | 0,07 | 0,14 |
| 0,10 | 0,70 | 0,70 | **1,40** |
| 1,00 | 7,00 | 7,00 | 14,00 |
| 2,00 | 14,00 | 14,00 | **28,00** |

El ejemplo adicional `0.10 lotes = USD2.80` exigiría en cambio **USD28 por lote round-trip**, de donde `2 lotes = USD56`. Se ejecutó aparte la sensibilidad **USD28/lote** para representar dicho ejemplo, pero **no se mezclan las dos tarifas** en el control canónico. Para USD14/lote, USD2,80 corresponde a **0,20 lotes**.

**Hecho oficial (separado del escenario conservador pedido):** el FAQ de FundedNext para Stellar Instant especifica Forex **USD7 por lote cobrados únicamente al abrir**, sin comisión al cerrar; materias primas 0,0016% nocional, índices sin comisión. Referencia: https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account. El usuario puede querer duplicar como estrés de costes; jamás atribuir la tarifa duplicada a FundedNext sin documento contractual.

## 12 escenarios H9b reejecutados (2019-07-01 a 2022-06-29, 3.368 señales originales)

Cuenta inicial USD2.000; trailing max loss obligatorio 6% desde USD1.880, presupuesto diario **voluntario** USD60, riesgo agregado instantáneo presupuestado USD60; sizing por lote mínimo e incrementos reales del manifest, estimación de margen, provisión de futuros costes al cerrar, no usar outcome para sizing y fail closed al primer evento no financiable/breach.

| Fee por lote roundtrip | Presupuesto trade USD | Estrés ejecución | Fills antes de interrupción | Saldo en interrupción USD | Comisiones ya pagadas USD | Estado |
|---|---:|---:|---:|---:|---:|---|
| **14** | **10** | 0R | **55** | **1.879,48** | 141,40 | **INCUMPLE MLL 6%** |
| **14** | **20** | 0R | 13 | 1.889,25 | 85,75 | Entrada mínima no financiable |
| **14** | **40** | 0R | 8 | 1.928,37 | 98,84 | Margen mínimo no financiable |
| **14** | **20** | +0,25R | 12 | 1.879,81 | 75,88 | **INCUMPLE MLL 6%** |
| 28 (estrés) | 10 | 0R | 29 | 1.892,36 | 119,84 | Entrada mínima no financiable |
| 28 (estrés) | 20 | 0R | 12 | 1.879,95 | 105,00 | **INCUMPLE MLL 6%** |
| 28 (estrés) | 40 | 0R | 8 | 1.891,38 | 102,90 | Entrada mínima no financiable |
| 28 (estrés) | 20 | +0,25R | 10 | 1.879,76 | 92,68 | **INCUMPLE MLL 6%** |
| oficial por instrumento | 10 | 0R | 70 | 2.091,04 | 66,86 | Margen mínimo no financiable |
| oficial por instrumento | 20 | 0R | 35 | 2.120,47 | 56,55 | Margen mínimo no financiable |
| oficial por instrumento | 40 | 0R | 8 | 2.026,67 | 17,01 | Margen mínimo no financiable |
| oficial por instrumento | 20 | +0,25R | 35 | 2.010,29 | 48,55 | Margen mínimo no financiable |

**CERO casos pudieron completar las 3.368 señales.** La cantidad `fills` muestra únicamente entradas realizadas antes de interrupción. El saldo en interrupción NO es saldo final probado de un portafolio si hay posiciones abiertas. En dos controles de USD14/lote hay incumplimiento del MLL observado en las liquidaciones terminales; falta verificar equity flotante histórica entre timestamps para certificar cuándo habría sido el primer incumplimiento real.

## Evidencia nueva de costes de las 3.368 señales

La suma **hipotética** sobre cada **lote mínimo** del manifest asciende a **USD1.081,36** usando USD14/lote, o **USD2.162,72** con estrés USD28/lote. Son costes presupuestarios de posibles entradas, **no comisiones efectivamente pagadas**. Días con suma de cargos mínimos superior a USD60: **0** bajo ambas estructuras de lotaje mínimo; las 774 jornadas de señales fueron auditadas. No reusar el antiguo `3368*USD7 = USD23576`: ese modelo fijo por trade era incorrecto bajo la premisa del usuario.

## Código y archivos reproducibles del replay local (NO declarar publicados en GitHub sin subida)

- `cibo_stellar_instant_2k_replay.py`: comisión proporcional `roundtrip14lot`, cronología 7/lote open y 7/lote close, obligación de reservar coste de salida; `roundtrip28lot_stress`, `official`.
- `test_cibo_stellar_instant_2k_replay.py`: seis pruebas unitarias (incluye 2lot→USD28, 0.10lot→USD1.40 y sensibilidad 28lot→USD2.80) — **6/6 PASS local**.
- `cibo_stellar_instant_2k_results_corrected.json`: 12 escenarios con 3.368 señales auditadas, fallos y fees cronológicos.
- `cibo_stellar_instant_2k_scenarios_corrected.csv`, `cibo_stellar_instant_2k_all_3368_signals_costs_corrected.csv`, `cibo_stellar_instant_2k_daily_signal_density_corrected.csv`.
- Informe humano `CIBO_STELLAR_INSTANT_2K_COMMISSION_CORRECTION_H9B_2026-10-08.md`.
- Fuente inmutable: historical manifest artifact `11389331836`; legacy replay `11542321736` (ambos SHA256 pinneados en H9 anterior).

## Nunca presentar como cuenta fondeada viable

El modelo usa outcomes estructurales retrospectivos, sin bid/ask histórico/MTM intratrade, swaps, spreads, stops por tick, y usa contrato provider 2026 reconstruido sobre 2019–2022. Reglas/cargos se basan en el producto oficialmente publicado más el límite conservador del usuario; no es un contrato de ejecución del usuario. Al primer lote mínimo no financiable, el histórico se marca INVIABLE; la autoridad del Trader de lanzar entradas no implica poder generar margen inexistente. Los fallos de solvencia soberana de CIBO H8 siguen siendo bloqueadores.

**Próximo orden P0:** certificar costes y lotes reales, reconstruir equity flotante y margin stopouts, rediseñar sizing económico para una cuenta USD2k, y recién entonces volver a estudiar DD y compuesto. Prohibido certificar ganancias de casos interrumpidos.
