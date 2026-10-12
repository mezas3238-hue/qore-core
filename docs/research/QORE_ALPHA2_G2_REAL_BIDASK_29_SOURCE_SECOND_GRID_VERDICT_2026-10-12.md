# QORE-Alpha 2 — G2 real BID/ASK: fuente 29, calidad 34.800 instantes, cuarentena

**2026-10-12.** Nuevo resultado de ingeniería económica y auditoría de fuente, **NO prueba de rentabilidad.**

## Evidencia reproducible

| Auditoría | GitHub Actions | Exact HEAD | Estado |
|---|---|---|---|
| Linaje código cTrader volume original 12+21 | [#38287282241](https://github.com/mezas3238-hue/qore-core/actions/runs/38287282241) | a248f862a4111e65a19c4e0962d4cdfc183e41e4 | SUCCESS |
| 29 mercados BID/ASK reales; dos ventanas 2020 y 2023; SHA y decodificación independientes | [#38288561813](https://github.com/mezas3238-hue/qore-core/actions/runs/38288561813) | bffb5e8ff5bb9ce12e515bb2558d12001472d9a3 | SUCCESS 5/5 |
| Grilla fuente cada segundo pre-registrada, x29 mercados y 2 ventanas | [#38289175880](https://github.com/mezas3238-hue/qore-core/actions/runs/38289175880) | bad36b0be42a9825d86b6b569f943a16c02bd0ef | SUCCESS 14/14 |

Original inmutable fuente PR #849 run #38283737706, HEAD f8262bd7cdea1fbfb2287c3c1fe0dae3be2b0efc; auditor QA independiente PR #851. QORE-Alpha2 restauró artefacto original vía GitHub Actions y revalidó sus SHA, no ingirió credenciales, no colocó órdenes. Dos ventanas preconsumidas 2020-09-15 y 2023-09-19 de 10 minutos para 29 mercados; la tercera ventana original 2026-09-15 se dejó intacta a nivel de valores de precio.

**29/29 mercados, BID 37.430, ASK 37.342, 74.772 ticks reales de ventana**, sin extrapolar a 10 años ni a 33 mercados. Original SHA de los pares BID/ASK entero 1e5 y decimal verificado; ni NAS100/USTEC ni los 3 símbolos anteriores NZDUSD/XAGUSD/SP500 se incorporaron a este archivo nuevo por inferencia.

## Resultado pre-inscrito de calidad fuente

Pre-registro commit cfd82a0b0e7a36e2bd27181742123bcc137e5430, archivo QORE_ALPHA2_G2_QUOTE_29_SECOND_GRID_SOURCE_QUALITY_PREREG_2026-10-12.md. Grilla t = ventana UTC inicial + cada segundo de 0 a 599, edad de ambos lados <=5.000ms. Fuente event-time pseudo as-of, no reloj de recepción.

| Clase de calidad | Instantes (total 34.800) |
|---|---:|
| BID/ASK frescos con ASK > BID | **27.866** |
| BID/ASK frescos con ASK == BID | **4.297** |
| Un lado ausente o edad >5.000ms | **2.637** |
| BID/ASK frescos con ASK < BID | **0** |
| **Total** | **34.800** |

Descomposición auditada: 29 × 2 × 600 = 34.800 muestras fijas y completas; sin seleccionar horarios por rentabilidad. Código src/qore/research/alpha2_g2_29_quote_quality_grid.py con ensayos negativos y fuente original 29 firmada, resultado artifact #11764855653, SHA principal JSON 1d2193c7238c48e106f979e9f2311be5129017d66c9f30e437f88fc096fd998b.

## Política obligatoria de cuarentena para el posterior motor NET

1. **FALTA/STALE**: si no existen ambas series a edad máxima permitida, rechazar o censurar esa cotización. No rellenar con OHLC, último spread arbitrario o coste cero.
2. **ASK=BID**: etiquetar SOURCE_ZERO_SPREAD_QUARANTINED, **NO computar comisión ni ejecución gratis**. Las dos cotizaciones reales pueden coincidir por representación, redondeo, convención o microestructura; no certifica precio de fill y exige segunda fuente y muestras forward. Problema original QORE Native [#856](https://github.com/mezas3238-hue/qore-core/issues/856).
3. **ASK < BID**: rechazar mercado/cotización como crossed; aunque el conteo fijo fue 0, el motor debe rechazarlo igualmente.
4. **ASK > BID**: cualidad de una observación histórica, no es autorización para negociar. Exigir available_at en el mismo terminal/cuenta en el instante de decisión, contrato, símbolo, duración suficiente para entrada **y salida**, comisiones/swap/financiación, simulación adversa, noticias PIT y paper prospectivo. Event time histórico que se descargó en 2026 no demuestra latencia as-of del consumidor en 2020/2023.
5. No calcular PF/Sharpe/Sortino/DD NET ni comparar PnL W1/W2/W3 a partir de 20min por símbolo. Históricos 12 Atlas y 21 nuevo no están homologados a nivel de cuenta broker. W1/W2/W3 permanecen congelados con no-soporte; NO W4 en el mismo histórico.

**Estado persistente Alpha2: HISTORICAL_SOURCE_PARTIAL_PASS / QUALITY_SPARSE_ZERO_SPREAD_QUARANTINE / ASOF_EXECUTION_UNVERIFIED / NET_BLOCKED / UTC001_BLOCKED / CERTIFIED 0.**

## Piloto propio cTrader independiente bloqueado

Solicitud DEMO read-only EURCHF ventana 2023-06-12 (prereg antes de fuente). [Run #38287610751](https://github.com/mezas3238-hue/qore-core/actions/runs/38287610751): preflight 14 tests sintéticos PASS, autenticación/solicitud de fuente bloqueó de modo seguro (código AUTH_OR_SOURCE_UNAVAILABLE_SAFE_BLOCK); manifestó bloqueo firmado, sin órdenes ni refresh. No confundir estos intentos con los 29 mercados anteriores recuperados por otro arquitecto. Decoder propio se corrigió para tiempo y precio signed deltas de cTrader, no reabrió históricos. Usar prioridad fuente compartida demostrada antes que repetir solicitudes inútiles.
