# VT31 — BASE BID/ASK DEL USUARIO: ESCENARIO DE SPREAD FIJO 1,60 EN 3Y NAS100 M1

**Fecha:** 2026-10-12. **Responsable:** Arquitecto 1 / COG. **Estado:** CI COMPLETADO, escenario económico de precio únicamente, sin ejecución de broker.

## Instrucción del propietario ejecutada

El usuario entregó una captura MT5 donde el símbolo mostrado **NDX100** presenta **Bid = 30853.00** y **Ask = 30854.60**; spread **1.60** unidades de precio. Este estudio **sí utiliza exactamente el spread de la captura como BASE FIJA de simulación en todos los cierres M1 históricos**. No se necesitan más capturas para este ensayo.

Para no insertar absurdamente el precio ABSOLUTO de 30853.00 en octubre de 2023 (cuando el índice tenía otro precio), el único parámetro temporalmente extrapolado es la **diferencia Ask-Bid = 1.60**.

Formalización aislada:

```text
M1_NAS100_mid_hypothetical = historial NAS100 M1 OHLC
Bid_simulado(t) = M1_mid_hypothetical(t) - 0.80
Ask_simulado(t) = M1_mid_hypothetical(t) + 0.80
LONG buy-limit CE -> condición exploratoria Ask_simulado_LOW <= CE
SHORT sell-limit CE -> condición exploratoria Bid_simulado_HIGH >= CE
```

**Advertencia de procedencia indispensable:** el archivo histórico NAS100 no está independientemente certificado como una serie MID; podría ser BID u otra referencia. El símbolo del snapshot es **NDX100 MT5**, cuya equivalencia numérica/contractual con el **NAS100 del replay** permanece sin demostrar. Las funciones reconstruyen precios **HIPOTÉTICOS**, NO un histórico real de bid/ask. El spread real varía por horario, volatilidad, liquidez y broker. Tampoco es una prueba de ejecución: un quote compatible con CE no constituye ACK ni fill. Los casos con CE+cancelación dentro de la misma M1 siguen indeterminados.

## Evidencia reproducible, sin cambiar la política VT31

[GitHub Actions RUN **38257774657 — SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38257774657), código exacto **`90deb73a47cbc09b88580595800607f2516323b7`**, artefacto **`11750991244`**. **35/35 pruebas aprobadas**, incluye pruebas exactas del Bid/Ask de la captura, LONG contra Ask, SHORT contra Bid y límites M1 sintéticos. Fuente M1 histórica de NAS100 **1,059,784** barras desde 2023-10-01 hasta 2026-10-01; SHA256 de fuente congelada `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`, primer FVG original de cada ventana exactamente idéntico **2,140** y p0 OPS sin cog **0**. Un único trader VT31, Londres y NY compartidos, sin modificaciones a `cognition.py` o `operations.py`.

Nuevas piezas:
- `src/qore/infrastructure/traders/vt31_ict_cleanroom/fixed_spread_quote_scenario.py`: snapshot real de usuario y fórmula MID +/-0.80 para simular el lado cotizable.
- `tests/infrastructure/test_vt31_fixed_spread_quote_scenario.py`: 6 tests de cálculo exacto y direccionalidad compra/venta.
- `scripts/vt31_shadow_ab_3y_runner.py`: instrumentación adicional que sólo filtra el **primer M1 CE original no ambiguo** A y B con el lado de cotización inferido; conserva A/B original y sus estados.
- `.github/workflows/vt31-fixed-spread-1p60-3y.yml`: recupera e identifica por SHA el histórico original, 35 tests y ensaya el escenario completo con salida JSON. La nueva lógica NO reapertura oportunidades cuyo primer toque M1 fue insuficiente con spread, por eso el resultado es un **test de estrés del primer CE limpio**, no un backtest ejecutable general ni una reconstrucción de ticks posteriores.

## Valores efectivamente observados con escenario 1.60

| Fuente ventana | Candidatos M1 iguales A/B | A CE original OHLC | A primer CE respaldado por BID/ASK sintético | B CE original OHLC | B primer CE respaldado por BID/ASK sintético | Sólo B compatible | Sólo A compatible |
|---|---:|---:|---:|---:|---:|---:|---:|
| London SB | 766 | 115 | **77** | 263 | **165** | 102 | 14 |
| NY AM SB | 721 | 110 | **97** | 282 | **231** | 142 | 8 |
| NY PM SB | 653 | 76 | **58** | 244 | **181** | 128 | 5 |
| **Total** | **2,140** | **301** | **232** | **789** | **577** | **372** | **27** |

A queda con **232 / 2,140 = 10.84%** source-only CE compatible con su lado simulado; B **577 / 2,140 = 26.96%**. La ventaja NETAMENTE pareada de B es **(372 - 27) / 2,140 = 16.1215 puntos porcentuales**; B no ha sido demostrado rentable. El escenario de spread 1.60 reduce el conteo frente a OHLC puro: A **69** primeros CE originales no respaldados por lado quote reconstruido, B **212**.

El principal ensayo A/B preregistrado *no cambia*: A anterior 301 vs B 789 M1 CE no ambiguos, ventaja **+22.803738pp**, pero **B conserva 670/2140 = 31.308411% INDETERMINADOS**, superando máximo preregistrado 10%. Esta foto fija de spread NO reduce la incertidumbre de secuencia intraminuto: **NO PASA** gate, no autorizar B, producción, broker, CIBO ni LIVE.

## Los límites que se deben conservar siempre

1. Sólo existe un snapshot visual del MT5 con Bid y Ask **de un instante**; el reporte no lo llama "historial Bid/Ask". El precio base ABSOLUTO se usa únicamente en pruebas de quote actual, NO en velas 2023–2026.
2. No se conocen ticks reales `NDX100` correlacionados con velas `NAS100` ni hubo órdenes reales, comisiones, stop/target cotizados, timestamps broker ni reconciliación de fills. **0 ejecuciones comprobadas; profit factor, drawdown, Sharpe, Sortino y tasa de acierto son no calculables**. Los 35 tests prueban código y consistencia, no existencia de edge.
3. Las **619** ambigüedades de B por coexistencia en la misma M1 de CE y evento de terminación quedan sin resolver. El siguiente paso científico opcional es obtener ticks históricos fiables del mismo símbolo y broker. La tasa de incertidumbre no puede cambiarse por deseo o por spreads constantes.
4. El informe es una prueba independiente de fuente que conserva los 2,140 ids de candidatos, el histórico inalterado, ONE VT31 Londres+NY M1, Fresh Holdout sellado y cero exposición financiera.

**Dictamen:** se ejecutó la prueba solicitada usando literalmente **spread 1.60** derivado de Bid 30853.00 y Ask 30854.60. **Mejora cuantitativa de B en oportunidades potenciales; NO certificación, NO fills, NO nueva rentabilidad.**
