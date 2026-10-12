# QORE Native — 33 cotizaciones BID/ASK aportadas por owner: alcance y limitaciones

**2026-10-12, registro de recepción del chat; FECHA REAL DE LAS COTIZACIONES NO VISIBLE.** Tres screenshots muestran terminal de cotizaciones: BID a la izquierda, ASK a la derecha, últimos dígitos elevados son fracciones finales de cotización. Captura teléfono muestra **10:13**, cada cotización de pantalla muestra hora **16:13:xx** sin fecha/timezone verificable, algunas actualizan en segundos distintos; **no asegurar que cotizaran exactamente al mismo instante**. El owner confirmó expresamente que las columnas son BID/ASK. Fuente no probada como mismo broker, cuenta, plataforma o contrato que los **12 archivos históricos originales** de CIBO cTrader DEMO y los **21** archivos IC Markets cTrader DEMO.

## Testigos visuales (contenido textual en GitHub, imágenes adjuntas a chat)

| Pantalla aportada | PNG original conversación | SHA256 original PNG |
|---|---|---|
| 1 — cruces EUR/GBP, CHFJPY, NZDCAD | `1000920175.png` | `7e261efa1364cdf8613c2996b04065d6f1a57ffa819eb9e9c9f640d020fb2897` |
| 2 — mayores, NZD y CHF, plata | `1000920174.png` | `ab1382d78ccebd3deed5aad3d61c27cf9352729f5c04b2e390951640fc15fbf0` |
| 3 — índices, oro, GBPUSD, FX mayores y BTCUSD adicional | `1000920173.png` | `c8794c6d6630d9f5fc0f5e5c30d2c87e139609222a20f6dbb595ac9e7d3132f3` |

Se guardó un **ledger legible por máquina** [`docs/research/data/QORE_NATIVE_USER_BIDASK_SCREENSHOTS_33_SPOT_TRANSCRIPTION_2026-10-12.json`](../research/data/QORE_NATIVE_USER_BIDASK_SCREENSHOTS_33_SPOT_TRANSCRIPTION_2026-10-12.json) con valores literales BID/ASK, hora vista si visible, fuente screenshot y SHA por símbolo, y las tres comprobaciones de incertidumbre. NO se copiaron los PNG al repositorio: deben conservarse como adjuntos originales si se requiere auditoría posterior con los bytes exactos.

**Cobertura QORE Core 33/33:** 3 índices NAS100/SP500/US30, 2 metales XAUUSD/XAGUSD, 7 mayores FX y 21 cruces. **BTCUSD** extra está visible en screenshot 3 pero **EXCLUIDO** del universo 33 y del coste de QORE Native.

## Interpretación matemática — SOLO spread de una fotografía

`spread_quoted = ASK - BID`. Para comparación adimensional `spread_bps ≈ 10000 × (ASK - BID) / [(ASK+BID)/2]`, un supuesto de compra al ASK y venta al BID con midpoint inmóvil exige atravesar un spread pero **no incluye comisiones, swaps, latencia, slip, divergencia de broker ni bid/ask de la futura entrada/salida**. No se afirma fill en los precios impresos.

Ejemplos de las imágenes:

| Etiqueta screenshot (QORE) | Bid → Ask | Diferencia | bps aprox |
|---|---|---|---:|
| EURUSD | 1.11781 → 1.11782 | 0.1 pip | 0.0895 |
| CHFJPY | 190.443 → 190.458 | 1.5 pip | 0.7876 |
| GBPJPY | 209.905 → 209.923 | 1.8 pip | 0.8575 |
| NZDCHF | 0.46607 → 0.46617 | 1 pip | 2.1454 |
| XAUUSD | 4170.96 → 4171.34 | $0.38 sobre un onza representada en el precio | 0.9110 |
| XAGUSD | 60.603 → 60.658 | $0.055 sobre un onza representada en el precio | **9.0713** |
| NDX100 (`NAS100` candidato) | 30846.75 → 30848.35 | 1.60 puntos de índice | 0.5187 |
| SPX500 (`SP500` candidato) | 7817.14 → 7817.72 | 0.58 puntos de índice | 0.7419 |
| US30 | 51673.06 → 51675.04 | 1.98 puntos de índice | 0.3832 |

### Bloqueos explícitos

1. **GBPUSD muestra 1.32325 BID = 1.32325 ASK, spread 0**; puede ser instante de visualización/artefacto de actualización; **NO usar como evidencia de coste 0 sostenido**. `BLOCKED_ZERO_SPREAD_SNAPSHOT`.
2. **NDX100 ≠ texto NAS100** e **SPX500 ≠ texto SP500**. QORE previo tenía alias históricos cTrader `USTEC` y `US500`. Los nombres *podrían* referir mismos índices de referencia, pero **sin confirmar especificación contrato, broker/account y ticker ID** no son intercambiables. `BLOCKED_INDEX_ALIAS_UNVERIFIED` ambos.
3. **30/33 spreads** restantes pueden compararse solo **descriptivamente** como cotización de un instante. No pueden servir para backtesting histórico 2016–24 ni declarar certificado net. No están necesariamente sincronizados, ni son un histórico intradiario de expansión de spreads.
4. Aunque un método tenga gross medio > spread observado, eso no prueba rentabilidad histórica: el precio era otro, la sesión era otra, y faltan BID/ASK históricos, comisión, slippage, stop, parcial fills, swap y macro noticias PIT. No computar Profit Factor, Sharpe, Sortino, DD net desde este snapshot.

**Acción siguiente legítima:** conservar ledger SHA, pedir **identidad de cuenta/broker y símbolo exacto de contrato**, aclarar fecha/huso de capturas y programar captura **forward BID/ASK ticks en GitHub** con event time y receipt time, NO extendiendo valores de una foto a diez años. Para usarlo en pruebas de costes, hacerlo únicamente como ilustración **hypothetical one-snapshot stress** con todos los supuestos etiquetados y sin net certification.

**No órdenes, no traders certificados, no cambios en CIBO/Shared/QDLE/MT5/VPS/LIVE.**
