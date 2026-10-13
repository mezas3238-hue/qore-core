# VT31 — Puerta 2: Resultado de los cuatro regímenes PIT de volatilidad y tendencia

**2026-10-13. Dictamen científico `NO_REGIME_SELECTION_LIFT_DEMONSTRATED`.** Ninguna celda cruzó el gate preregistrado. **Dos celdas TREND UNDERPOWERED**, no falsadas. **NO es edge económico ni ablation de COG aislada.**

## Procedencia, orden temporal e invariantes

- **Preregistro** antes de escribir runner/test `docs/research/VT31_GATE2_REGIMES_PIT_PREREG_20261013.md`, commit `78cfa3c55487df620c450e0b12c6c26537dc683b`. El workflow verifica `git merge-base --is-ancestor`.
- **[CI #38430665167 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38430665167)**, código/test/workflow evaluado commit `236c189c5142bea11308a9d46a10010e6a6e2371`, **6/6 tests adversariales PASS**, Ruff, compile, checksum original y SHA256 manifest PASS. Artefacto numérico **`11831130629`**, `gate2-4-regimes.json`.
- Fuente 3Y desarrollo NAS100 M1 inmutable **1.059.784 M1**, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, artifact original `11459859004`. Ledger de 2.140 ofertas COG+OPS source-only SHA256 `e9683d87f0645b488968aeb3e207347649f4e9aea5c535202ab4f024c22e7646`, artifact `11657461650`; **0 fills**.
- Benchmark Gate1 PR #910 reproducido exactamente **2.286 ventanas**, **2.140** fuentes COG+OPS, diferencial pareado COG+OPS vs primer FVG bruto **−0,954117 pts**. No reentrenamiento, nuevos umbrales, reconstrucción posterior de outcomes ni modificación de ventanas 03/10/14 NY.
- Régimen al INICIO de la ventana, no en el FVG: volumen (volatilidad por suma de cambios absolutos M1; no volumen negociado) de **las 60 M1 anteriores** vs mediana 20 referencias de la misma ventana en fechas anteriores; eficiencia direccional del prehour `|last_close−first_close|/sum(|diff_M1|)`; `TREND≥0,35` o CHOP; `HIGH_VOL` si diferencia realizada supera mediana 20 anteriores. **Todo PIT, DST-aware**; 20-period warmup y ventanas faltantes = UNKNOWN (nunca reparadas retrospectivamente). Estos son umbrales QORE elegidos antes de resultados, no categorización ICT o TTrades.
- Prueba primaria por celda: diferencia `retorno COG+OPS desde próxima M1 a +15m − retorno primer FVG bruto misma ventana desde su propia próxima M1 a +15m`, n 2.000 bootstrap de bloques semanales; **cuatro IC bilaterales 98,75% (Bonferroni FWER ~5%)**. `n≥100`, `≥20 semanas`, delta positivo con límite inferior IC>0 y media seleccionada positiva para declarar un `EXPLORATORY_POSITIVE` que todavía necesitaría OOS. Resultados nunca elegidos tras ver rentabilidad.

## Tabla de resultados completa

| Estado original a 03/10/14 NY | Ventanas completas con ese estado | VT31 COG+OPS admitidos | Media seleccionada BRUTA +15m, pts | Media RAW todas las ventanas del estado, pts | Delta pareado seleccionado−raw, pts | IC98,75% delta | Dictamen |
|---|---:|---:|---:|---:|---:|---|---|
| **HIGH_VOL_TREND** | **51** | **41** | **+6,197805** | +2,372157 | **+5,056829** | **[−16,206804; +29,131836]** | **UNDERPOWERED** |
| **HIGH_VOL_CHOP** | **1.042** | **972** | **−2,976224** | −0,865681 | **−1,618745** | [−5,205739; +2,256438] | **NO_SUPPORT** |
| **LOW_VOL_TREND** | **50** | **46** | **−2,651739** | +2,112200 | **−2,450870** | [−15,759949; +10,412132] | **UNDERPOWERED** |
| **LOW_VOL_CHOP** | **1.082** | **1.028** | **−1,362763** | −0,273993 | **−0,444630** | [−2,754158; +2,098656] | **NO_SUPPORT** |
| `UNKNOWN_WARMUP` | **58** | no estimar | — | — | — | — | **UNKNOWN** |
| `UNKNOWN_PREWINDOW` | **3** | no estimar | — | — | — | — | **UNKNOWN** |

Totales: **2.225** ventanas clasificadas, **61 UNKNOWN**, **2.286** completas; **2.087** señales admitidas dentro de las cuatro celdas, **53** señales aprobadas con régimen UNKNOWN y **146** ventanas sin señal COG+OPS. Ninguna celda tenía datos posteriores incluidos en la etiqueta.

### Inferencia y cobertura

- IC95 semanal descriptivo de delta: HIGH/TREND [−11,983890;+23,550102], HIGH/CHOP [−4,583773;+1,462133], LOW/TREND [−13,192747;+8,274349], LOW/CHOP [−2,359887;+1,616301].
- IC95 de retorno seleccionado: HIGH/TREND [−2,909394;+16,172444] (41 casos, 38 semanas), HIGH/CHOP [−5,954440;−0,141801] (972;146 semanas), LOW/TREND [−12,903863;+8,657936] (46;41), LOW/CHOP [−3,009899;+0,219149] (1.028;142).
- Sesiones y año no fueron usados para seleccionar ganadores. Tabla fuente en JSON conserva recuentos por ventana 03/10/14 NY, desfase propio y fracción de direcciones iguales.
- **Las 41 señales HIGH_VOL_TREND son positivas como media exploratoria**, pero su delta simultáneo es compatible tanto con pérdida enorme como mejora enorme y su IC de retorno propio incluye cero. No declarar `REGIME_EDGE` ni usar el estado como filtro productivo.
- **Rango representa 2.070 señales**, trend 87 de las 2.087 clasificadas. La métrica de eficiencia≥0,35 de prehour produce **muy baja potencia en trend** en esta fuente. No bajar umbral tras ver que falta muestra: sería otro test / p-hacking.
- **COG puro no identificable**: el ledger original sólo registra primera oportunidad admitida por el stack conjunto COG+OPS, con tiempos y direcciones no siempre iguales al RAW. Diferencias en instante de entrada/side contaminan el delta; COG única exigiría registrar aprobar/rechazar al MISMO FVG, hora y dirección y evaluar separadamente. El avance es de selección conjunta, no de supuesta cognición humana acertada.

## Decisión / siguiente trabajo finito

**Puerta 2 NO_SUPPORT para mejora condicional de COG+OPS en CHOP; TREND queda UNDERPOWERED.** Ausencia de evidencia favorable con estas reglas preregistradas, **NO falsación absoluta del régimen ni del Silver Bullet original**.

**Puerta 3** = calendario macro **point-in-time** auténtico de fechas *y horas* FOMC/CPI/NFP (y zona horaria), construido de fuentes oficiales verificables; no inventar eventos ni confundir fechas de observación económica con fecha de publicación; definir ventana prohibida antes de outcomes; si calendario históricamente incompleto/ambiguo dictamen `BLOCKED_CALENDAR_PIT`, NO un NO_SUPPORT fabricado.

**Puerta 4** = CE LIMIT / SL C2 / DOL, con cronología broker BID/ASK, contrato y costes auténticos, motor OMS/ACK y G3 con firmas válidas. Hasta eso: `ECONOMIC_EDGE_NOT_IDENTIFIED`, producción/live prohibidos.

**No cambiar** G3 PR #896 acta `a446afa17ed6e411b8f0b6fc182b103a78959a97` y código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` sin firmas; 3Y desarrollo consumido, Fresh Holdout no abierto, no merge ni VPS.
