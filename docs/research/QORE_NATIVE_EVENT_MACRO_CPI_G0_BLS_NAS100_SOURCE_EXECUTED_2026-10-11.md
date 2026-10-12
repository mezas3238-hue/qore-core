# QORE Native EVENT-MACRO CPI — G0 ejecutado: calendario BLS y NAS100 CIBO M1, SIN RETORNOS

**2026-10-11 America/Asuncion — G0 `SOURCE_METADATA_COVERAGE_ONLY` con restricciones materiales.** Solo procedencia/calendario/timestamps y conteo de M1; NO CPI sorpresa, NO retornos o PnL, NO fills/costes, NO estrategia ni decisión G1 económica. Prereg G0 anterior a la lectura de fuente, commit **`621c55ffc21d31305fe0f623cb9822b7b7b2b476`**. PR #807.

## Ejecución efectivamente comprobada

- [GitHub Actions #38189483643](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643), code HEAD probado **`5da94a97eba2c8286f46ecfe4bfbb27fed2b3dfe`**: **3/3 jobs SUCCESS**, quality **9/9 pruebas PASS** y Ruff PASS. Primera corrida #38189440270 falló por un import sin usar; se corrigió sin alterar hipótesis ni resultados.
- BLS **fuente primaria**: `https://www.bls.gov/schedule/2016/` ... `/2026/`. **11/11 calendarios HTTPS** parseados de filas CPI (0 fechas inventadas) y hashes `source_html_sha256` por año. [Artifact BLS #11720651765](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643/artifacts/11720651765). **131 filas totales de calendarios** 2016–2026; las de fines de 2026 incluyen programaciones **futuras** al día de esta ejecución y no deben llamarse publicaciones históricamente realizadas. **119** eventos programados dentro de la muestra CIBO (desde 2016-09-17 hasta 2026-09-17 UTC excl.).
- La excepción oficial documentada queda preservada: **año de publicación 2025 = 11 filas CPI**, no 12; el archivo BLS explica que CPI del mes de referencia **octubre 2025 no fue publicado** por interrupción de financiación federal. CPI del mes de referencia septiembre 2025 se publicó **24/oct/2025 a las 08:30 ET**, ver `https://www.bls.gov/news.release/archives/cpi_10242025.htm`. No confundir mes referencia con fecha de anuncio, ni inventar una fecha faltante.
- CIBO NAS100/USTEC original cTrader DEMO provider-native M1 [run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334) artifact **#10618862813**, **3.486.929 M1** con **11/11 SHA256 RAW_M1_LEDGER** y manifest SHA verificados, UTC estricto, sin descargar datos nuevos ni llamar cTrader. Fuente posterior a 2016 solamente, ningún acceso OHLC sellado pre-2016. Solo se consultaron columnas de identidad y `opened_at` / `utc_timestamp_in_minutes`; **NO** se accedió a `open_relative/high_relative/low_relative/close_relative`, volúmenes, forward returns o direcciones. Report `zero_price_values_consumed=true`, `zero_economic_outcomes_calculated=true`.
- [Artifact exacto cobertura #11720822239](https://github.com/mezas3238-hue/qore-core/actions/runs/38189483643/artifacts/11720822239); `cpi-nas100-m1-g0-coverage-report.json` SHA256 `19fcb1af8b45bc979a0eaf4dfe35958a5cc263e1ebdde9495bf345e71d099b66`; `cpi-nas100-m1-g0-event-presence.json` SHA256 `648b10a01ae7610cfad66619db7ec9833679afe4774c48f141c4af8e82de25d5`. Ambos SHA coinciden independientemente con `OUTPUT_SHA256SUMS.txt`. Lista de 119 fechas comprobada, sin información de precios.

## Corte NOMINAL de datos M1 (no fills ejecutables)

Puertas predefinidas por evento 08:30 New York DST: 08:20–08:29 (10), 08:30 (1), 08:31–09:00 (30), 09:01–09:30 (30), en total **71 timestamps** por CPI. No hay interpolación ni sustitución de una vela faltante.

| Fuente | Resultado |
|---|---:|
| Años calendario BLS oficiales | **11/11** |
| CPI en ventana CIBO, marcas de calendario BLS | **119** |
| CPI con 71/71 M1 originales presentes | **113/119** |
| Fechas con 0–70 velas presentes | **6/119** |
| M1 provider native verificadas por SHA | **3.486.929** |
| CPI calendario años 2016, 2017–24, 2025, 2026 en rango | 3, 12/año, 11, 9 |
| Coste de spread/fricción al CPI | **DESCONOCIDO** |
| Consenso CPI historizado as-of | **NO VERIFICADO** |
| Comprobación comunicado publicado fecha a fecha | **PENDIENTE** |
| G1 con edge probado | **NO HECHO** |

Seis fechas sin 71/71 slots:
- `2017-01-18`: PRE10=10, PRINT0=1, AFTER30=30, AFTER60=29.
- `2017-03-15`: PRE10=10, PRINT0=1, AFTER30=28, AFTER60=30.
- `2017-04-14`: **0** en todas las ventanas; coincide con un viernes de probable calendario festivo, pero **no inferir cierre/feriado broker ni eliminar sin evidencia independiente**.
- `2017-05-12`: PRE10=10, PRINT0=1, AFTER30=30, AFTER60=29.
- `2020-04-10`: **0** en las ventanas; también requiere verificación de calendario de mercado, no imputar.
- `2022-12-13`: PRE10=10, PRINT0=1, AFTER30=29, AFTER60=30.

CPI programado a las 08:30 ET con una vela nativa fechada 08:30 **no demuestra** que pudiera abrirse una posición exactamente a las 08:30:00 ni que no hubiese ampliación extrema del spread.

## Interpretación y restricciones de investigación

- El censo prueba **viabilidad cronológica del estudio** con 113 fechas nominalmente cubiertas, no capacidad de capturar una sorpresa ni suficiente potencia estadística para un futuro alpha. 113 releases nominales, no 3.49 millones de oportunidades independientes; cada CPI es un cluster/mes.
- Los calendarios BLS `/schedule/YYYY/` fueron consultados **retrospectivamente**. La fecha actualmente listada no garantiza que la fecha planeada se conociera exactamente desde una fecha t previa; tampoco demuestra que el comunicado **efectivamente salió a esa hora** sin cotejo con original `/news.release/archives/cpi_MMDDYYYY.htm`.
- **CPI sorpresa** = realizado inicial de primera publicación menos expectativa de consenso **registrada antes del anuncio**. BLS entrega comunicado/datos realizados y archivo, pero no un feed histórico de consenso fechado as-of; no inventar consenso con revisiones, último CPI o valores posteriores.
- **Costes**: se necesitan spread históricos NAS100/USTEC alrededor de CPI, slippage/volatilidad/latencia, tarifas y contratos reales. M1 sin BID/ASK no acredita estos costes. No es necesario para censo de presencia, sí para certificar regla económica.
- Potencia: máximo nominal 113 días completamente cubiertos en esta muestra; bajo volatilidad/sorpresa heterogéneas, puede que sea insuficiente para un IC de alpha neto que supere costes por un margen relevante. **No calcular tamaño de efecto esperado basado en retornos aún ocultos**. Diseño posterior deberá fijar mecanismo, materialidad y potencia, o `INSUFFICIENT_POWER`.
- **No** escoger 113 fechas como "ganadoras": las seis restantes son missingness/hora/mercado y requerirán justificación as-of. No seleccionar volatilidad por resultados.
- **Estado:** `EVENT_CPI_G0_CALENDAR_AND_M1_METADATA_PASS`; bloqueos `RELEASE_ACTUAL_CONFIRMATION_PENDING`, `CONSENSUS_ASOF_UNVERIFIED`, `CPI_TIME_COST_UNVERIFIED`, `BROKER_CALENDAR_UNVERIFIED`; **NO permiso de G1 económico hasta su resolución o prerregistro de estrategia que no requiera consenso**, evidencia de primer fill y potencia.

## Próximos trabajos autorizados — metadata only

1. **G0B confirmar publicación CPI realizada**: cotejar `/news.release/archives/cpi_MMDDYYYY.htm`, embargo 08:30 local y mes referencia **sin procesar contenido económico**; registrar calendario con cambios especiales 2025 y fechas efectivas distintas.
2. **G0C investigar fuente institucional/licenciada de consenso preliminar** de CPI núcleo/mensual, con timestamp pre-release, historial revisiones, integridad y licencia, **sin leer para PnL**.
3. **G0D coste del broker en CPI**: localizar telemetría de cuentas cTrader/ejecución histórica y determinar si existe evidencia de BID/ASK real y condiciones de ejecución; solo inventario (no recopilar credenciales, no tocar VPS ni órdenes).
4. Preparar **análisis ex ante de potencia** y un primer mecanismo falsable de captura de sorpresa CPI con procesamiento first-online. Si no hay fuente as-of o costes, `G1_BLOCKED`, sin más exploración de retornos.

**Todos los trabajos en GitHub; cero trader, cero certificar, cero LIVE/VPS/MT5.**
