# VT31 TTrades AM — Resultado fuente limpio, 3Y, STOP/GO exploratorio

**Corte 13-10-2026.** No es el VT31 anterior. Variante nueva `VT31_TTRADES_AM_FVG_SOURCE_ONLY_V0`, **FVG-only, no replica todos los modelos TTrades**. No hay cotizaciones BID/ASK, fills, órdenes ni PF. Negar certificación; no declarar que TTrades o ICT pierdan dinero.

## Procedencia y orden causal

1. [**Contrato de investigación preregistrado antes del código y de las mediciones**](https://github.com/mezas3238-hue/qore-core/blob/fd9fde9a57b04a822d6296e7a858761eeb68fc83/docs/research/VT31_TTRADES_AM_SOURCE_MODEL_PREREG_2026-10-13.md), commit `fd9fde9a57b04a822d6296e7a858761eeb68fc83`; el workflow comprueba que es antecesor Git de la ejecución (fetch-depth 20).
2. **[CI #38405397695 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38405397695)**, código/test/workflow SHA **`8a36203f6adb567b215c28a1aa8234bb88321544`**, **11/11 pruebas de frontera PASS**, Ruff/compile, hash SHA256 de M1 y manifiesto de salida PASS; artifact **`11818681506`**.
3. Fuente exclusiva: NAS100 M1 original 2023-10-01 a 2026-10-01 (exclusive), **1.059.784** M1, SHA256 **`0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`**, artifact **`11459859004`**. NO reusar 2140 señales antiguas ni 222 del censo, tampoco la cohorte G3 V1 sin firmar. El desarrollo 3Y ya está expuesto en investigaciones previas, así que la prueba es **exploratoria**, NO OOS.

## Una nueva población construida EX ANTE, desde las M1, sin PnL

| Estado final de la jornada NY | Conteo |
|---|---:|
| `SOURCE_ONLY_CANDIDATE` (barrido + desplazamiento + primer FVG + geometría) | **205** |
| `NO_DISPLACEMENT` (hubo barrido pero no reversión impulsiva según nuestro proxy) | **456** |
| `NO_SWEEP` | **65** |
| `DOUBLE_SWEEP_AMBIGUOUS` (ambos extremos barridos antes de confirmar propuesta) | **36** |
| `NO_VALID_FVG` | **7** |
| `MISSING_REFERENCE_H1` | **4** |
| `MISSING_SB_HOUR` | **2** |
| **TOTAL jornadas con fragmento 09/10/11 observado** | **775** |

La relación propuestas/jornada es **205/775 = 26,45%**, no win rate; no se ha confirmado ninguna orden ni ejecución. El swing stop de referencia usa extremo barrido antes de FVG, sin rejilla/tick/buffer broker y no se puede convertir en SL operativo. `NO_DISPLACEMENT` es adjudicación respecto del filtro cuantitativo **QORE** (ATR20 `body>1.5×ATR` y `body/range≥0.70`) no especificado numéricamente por TTrades; las reglas no se ajustaron para rescatar resultados.

## Único screening direccional bruto, SIN entrada CE

| Control | Resultado |
|---|---:|
| Subconjunto con nueva señal y 16 M1 continuas posteriores | **205/205** |
| Retorno bruto 15m desde próxima apertura M1, media | **−1,445951 puntos de índice** |
| Fracción de movimientos favorables a 15m | **0,453659 (45,37%)** |
| Semanas ISO con muestras | **116** |
| IC bootstrap semanal 95%, 2.000 extracciones | **[−8,696861; +6,558556] pts** |
| Spread, comisiones, lotaje, slippage, órdenes | **NO**; no imputar 1.60 del NDX100 MT5 |
| PF, DD, Sharpe, Sortino, expectativa neta de LIMIT CE | **NOT_IDENTIFIED** |

**Interpretación:** promedio bruto negativo pero **intervalo cruzando cero**: se observa **ausencia de respaldo estadístico positivo**, no evidencia estadística concluyente de un retorno medio negativo. El screening a OPEN fijo no analiza CE, swing stop, DOL TP, ni entrada por OB/breaker; tampoco se puede comparar 205 con los antiguos 2140 como estrategia A/B (poblaciones y modelos distintos). **NO GO para financiación o certificación de esta variante FVG-only**, y **NO SUPPORT** para hipótesis de predictividad neta aún no examinada. Se requiere fuente bid/ask de mismo contrato y nuevo estudio OOS para cualquier afirmación económica.

## Límites de fidelidad pendientes (no falsear `FULL_TTRADES_REPLICA`)

- **Sí implementado de forma causal**: H1 NY 09–10 ya cerrado completo y reloj DST, barrido del extremo antes de proponer, LONG tras LOW / SHORT tras HIGH, reversión con vela de displacement posterior al barrido, FVG 3M1 posterior, target EXACTO en el otro extremo H1.
- **Solo QORE formalizado, NO texto literal TTrades**: ATR20 1.5; ratio 0.70; ambigüedad de doble barrido; primera oportunidad; FVG-only; CE precio de referencia; geometría `sweep_extreme−CE−H1target`, sin fill. El criterio de reversión comprueba el **cruce del borde barrido** (`close>H1.low` LONG / `close<H1.high` SHORT), no comprueba explícitamente el cierre estrictamente entre **ambos** extremos H1; revisar doctrinalmente antes de afirmar fidelidad total. El sweep extremo puede ampliarse antes de la propuesta de FVG: es un proxy de stop swing, no garantía del swing causante del desplazamiento.
- **No implementado**: entradas por order block y breaker, otras confirmaciones discrecionales que exija TTrades, detalles de stop del swing efectivo, gestión RR, órdenes, bid/ask tick, volumen, fees, NQ futures feed. El NAS100 CFD de nuestro M1 **NO es NQ** ni se ha certificado equivalencia.
- La fuente primaria [TTrades 2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/) describe la variante AM; [ICT 2023](https://www.youtube.com/watch?v=tRq1hyGGtl4) describe Silver Bullet más general. Una tercera implementación de código en Internet no se considera autoría primaria ni prueba de rendimiento.

## Decisión administrativa y continuidad

**`NO_GO_MORE_UNFUNDED_TTRADES_FVG_ONLY_G6_G7_NOW`**. Se completó un detector nuevo y una prueba rápida reproducible; no se encontró una señal direccional bruta favorable que justifique construir un nuevo OMS o pagar datos sin evidencia adicional. Conservar material y sin retoques post hoc. Si se requiere **fidelidad total a TTrades**, faltan exactamente OB/breaker, definir desplazamiento+stop mediante ejemplos primarios con testigos as-of, NQ vs CFD, luego preregistrar una **variante futura claramente distinta**, antes de mirar nuevos resultados; nunca reetiquetar esta versión como estrategia original ni buscar ganadores en 205.

**G3 anterior intacto**: acta `a446afa17ed6e411b8f0b6fc182b103a78959a97` + código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`, sigue sin dos firmas. Ningún cambio en VPS, producción, PnL, holdout o estado LIVE.
