# VT31 TTrades AM — Cuatro familias de entrada incorporadas y examinadas

**2026-10-13 · MODELO NUEVO AISLADO, sin tocar el VT31/G3 existente.**
**Dictamen de ingeniería:** `ALL_FOUR_ENTRY_SOURCE_FAMILIES_IMPLEMENTED`.
**Dictamen económico:** `EDGE_NOT_IDENTIFIED`; `NO_LIVE`, `NO_CERTIFICATION`.

## 1. Versiones y testigos

- Preregistro **anterior** a la implementación y al screening: commit SHA completo **`0a3ee8a7c307d2adf7cdda24eb609732c2e703a1`**, `docs/research/VT31_TTRADES_AM_ALL_ENTRY_MODELS_PREREG_2026-10-13.md`, cronología de Git comprobada por CI. Sin reajustes numéricos después del screening.
- **[GitHub Actions #38408896599 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38408896599)**, código exacto **`f702321cad8c0cef1e783f718b5de3028a6b1aba`**; **11/11** tests sintéticos PASS, Ruff/compile PASS, frozen market SHA256 PASS, artifact **`11820810755`**, manifest de evidencia SHA256 PASS. No se utilizó ningún quote BID/ASK ni señal con autoridad de trading.
- Fuente: M1 NAS100 CFD periodo 2023-10-01 a 2026-10-01 exclusivo, **1.059.784** M1, SHA256 **`0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa`**, artifact `11459859004`, **775** jornadas NY con fragmentos 09–11. Reprocesa M1 original desde cero: **NO** recicla la cohorte antigua 2140 ni 205 FVG v0. Todo esto es **desarrollo ya observado**, no OOS nuevo.
- Scripts: `scripts/vt31_ttrades_am_all_entry_sources_20261013.py`; pruebas `tests/infrastructure/test_vt31_ttrades_am_all_entry_sources_20261013.py`; workflow `.github/workflows/vt31-ttrades-all-four-models-20261013.yml`; todos **nuevos** en rama `agent/vt31-ttrades-all-entry-models-20261013`. Depende de utilidades M1 y ATR del v0 TTrades (PR #905), pero **no** cambia contratos, código trader ni metodología G3 #896.

## 2. Qué cuatro fuentes de TTrades se modelaron exactamente

En el [artículo primario de TTrades del 19-06-2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/), el barrido de H1 NY 09–10 antes de oportunidad NY 10–11 y el objetivo al extremo opuesto son explícitos. El autor enumera **displacement back into range, breaker blocks, order blocks, fair value gaps**. **No proporciona los detectores deterministas para order blocks/breakers ni umbrales ATR.** Los detalles de abajo son **`QORE_FORMALIZATION_PROXY`**, NO certificación de reconstrucción exacta del autor.

1. `DISPLACEMENT_DIRECT`: evento al cerrar la **primera** M1 que revierte después del barrido y cierra estrictamente dentro de H1 09–10 con impulso `body>1.5×ATR20` y `body/range≥0.70`. Precio teórico = ese cierre, NO mercado/ACK de broker.
2. `FVG_3M1`: primer patrón de 3 M1 consecutivos de dirección de reversión que confirma en o después de la M1 displacement, con C1 después del primer sweep, precio de referencia CE midpoint, NO limit fill.
3. `ORDER_BLOCK_RETEST`: última M1 de color contrario **previa al displacement y posterior/incluida a la barra sweep**, zona testigo de su mecha y cuerpo, referencia midpoint del cuerpo; primera M1 **posterior al displacement** cuya OHLC abarca ese precio. La señal se registra **después del cierre** de esa vela, nunca antes del toque como fill. Intra M1 stop/target simultáneo registra alerta de ambigüedad.
4. `BREAKER_RETEST`: último swing de 3 barras **confirmado en H1 09–10 antes del sweep**, precio superado en sweep y reclamado con cierre de displacement, primera M1 posterior que solapa el nivel. **Esto es un breaker-*level proxy***, no identificación canónica de una zona ICT breaker block con fallo de OB, la cual requeriría contrato más rico.

Se evalúan **las cuatro familias de forma independiente por día**, hasta una propuesta por familia/jornada, **no** cuatro órdenes reales. Se registran zonas y timestamps causales, side, swing stop *aproximado*, DOL H1 opuesto, geometría; si un día genera varias familias sus resultados **se solapan**. No hay selección de ganadores a posteriori ni consolidación arbitraria para fingir expectativa de cartera.

## 3. Resultados históricos exploratorios completos, sin coste ni ejecuciones

| Familia | N fuentes | Media bruta desde siguiente M1 OPEN, +15m | IC 95% bootstrap por semana | Semanas | Movimiento favorable/no winrate |
|---|---:|---:|---|---:|---:|
| **DISPLACEMENT_DIRECT** | **212** | **−1,464151** | [−7,976825; +5,431298] | 120 | 45,75% |
| **FVG_3M1** | **205** | **−1,445951** | [−8,696861; +6,558556] | 116 | 45,37% |
| **ORDER_BLOCK_RETEST** | **116** | **+1,865948** | [−5,870805; +9,801977] | 84 | 47,41% |
| **BREAKER_RETEST** | **84** | **+1,661548** | [−7,987427; +10,716443] | 73 | 48,81% |

**212 días** con al menos una familia de propuesta sobre 775, **NO** 617 operaciones diferentes: 212+205+116+84 = **617 fuentes solapables, no trades**. No multiplicar artificialmente el tamaño de la muestra ni sumar retornos como equity. Todos los IC semanales incluyen **cero**; ninguno constituye respaldo estadístico positivo al 95% y menos aún edge **neto**. El coste histórico, stop real, target exacto, BID/ASK y ejecución OMS ACK **NO están disponibles**. La comparación de medias entre familias, obtenidas en el **mismo desarrollo ya inspeccionado**, es una observación descriptiva, **no descubrimiento confirmatorio**.

**Hallazgo útil, todavía hipotético:** solo OB y breaker mostraron medias brutas favorables en screening fijo, mientras FVG/direct displacement fueron negativos. **No seleccionar OB/breaker para LIVE ni ajustar sus definiciones para extraer edge retrospectivo.** Si se desea confirmar la hipótesis, definir evaluación OOS **nueva e independiente** con entrada realmente ejecutable del mismo instrumento, no reutilizar esos 84/116 como ganador post hoc.

## 4. Limitaciones explícitas / qué NO se construyó

- **No son todavía modelos operables integrados** al trader `VT31Trader` ni a OMS, son detectores de **candidatos** en runner separado. No hay límite real de órdenes, fills LIMIT/market, stop broker/tick, BE, parcial o time-exit. `quote_bid_ask_and_order_ACK_count=0`, `live_trades=0`, `economic_pf_dd_sharpe=null`.
- El artículo TTrades detalla tipos de setups pero **no prescribe** matemáticamente la selección de OB/Breaker ni punto exacto de entrada. `BREAKER_RETEST` es un *proxy de retesteo de nivel pivote*, no breaker ICT integral. La única forma de elevarlo a alta fidelidad es validar con ejemplos audiovisuales específicos TTrades, ratificando zona OB que falló, secuencia temporal y precio.
- NAS100 CFD M1 no equivale por defecto a NQ futures, spreads/commissions/tick-grid desconocidos. **OHLC overlap** no prueba ni una orden enviada ni el orden tick de TP/SL. Precio de referencia de cada modelo **NO** coincide necesariamente con el OPEN empleado por el screening direccional.
- Todos los modelos requieren sweep del H1 de 09:00–10:00 y displacement verificable dentro de 10:00–11:00 NY en reloj DST. Una nueva regla distinta de ATR, RR mínimo, swing confirmación, tie-break o período después de ver estos resultados sería **`V2_NEW_PREREG`**, no una corrección retroactiva silenciosa.
- No usar conclusiones de una variante estrecha de TTrades para desmentir el ICT Silver Bullet original (3 ventanas y DOL diversos).

## 5. Decisión científica y próximos gates

**Completado el mandato de incorporar las cuatro familias como detectores causales de investigación.** Falta consolidación ejecutable y validación de fidelidad audiovisual en breaker, contrato de stop/ratio y orden ACK. Prohibido atribuir al submodelo edge por +1,66/+1,87 pts sin significancia, costes ni OOS.

1. Si la dirección del proyecto busca fidelidad autoral y no sólo etiquetas, **auditoría externa de reglas OB/BB sobre ejemplos TTrades** antes de autorizar integración operativa y sin modificar las mediciones de esta versión. Documento firmado/fixed SHA por roles COG/OPS.
2. Confirmar broker real con **NQ/NAS100 instrument identity**, ticks BID/ASK históricas, ticket_size, fees, secuencia stop/target y ACK, y registrar una política única de resolución multientrada (no elegir por PnL).
3. Crear motor independiente `SOURCE_ONLY -> ORDERS/ACK -> CLOSED_TRADE` sólo después de gate fuente+metodología. Ejecutar prueba independiente de expectativa neta y DD en holdout reservado autorizado. **En esta ronda** `NOT_IDENTIFIED`, `NO_GO_LIVE_OR_CERT`.
4. El G3 antiguo continúa **sin doble firma**, acta `a446afa17ed6e411b8f0b6fc182b103a78959a97`, código `78d4cdac0e09d1a6eef37b99c505ffc5098031fc`, PR #896 sin tocar ni re-firmar. No alterar ledger B51/619, VPS ni producción.

**Prueba reproducible**: [run #38408896599](https://github.com/mezas3238-hue/qore-core/actions/runs/38408896599) + artifact `11820810755`; reporte JSON bruto incluye testigos por familia, etiquetas y razones de rechazo.
