# QORE Futures A / M0 — cierre del preflight de fuentes GRATUITAS sin tarjeta

**Fecha:** 13 de octubre de 2026 (UTC). **Presupuesto autorizado para datos: USD 0.**  
**Informe basado en descarga real y análisis temporal de archivos públicos:** [GitHub Actions #38342603409](https://github.com/mezas3238-hue/qore-core/actions/runs/38342603409), código de chequeo `.github/scripts/qore_futures_a_m0_public_free_archive_preflight_v1.py`, estado runner `SUCCESS`.  
**Fuente adicional de contraste:** [GitHub Actions #38342546391](https://github.com/mezas3238-hue/qore-core/actions/runs/38342546391), escaneo de ZIP y archivos; no evalúa retornos.  
**Identidad de misión:** [#894](https://github.com/mezas3238-hue/qore-core/issues/894), [PR #895](https://github.com/mezas3238-hue/qore-core/pull/895). Sin reabrir FX QORE Native ADR #893.

## Decisión M0, con evidencia ejecutada

`BLOCKED_DATA_OR_LICENSE` **para iniciar investigación económica con fuente gratuita hoy**. Ni los ZIP públicos TurtleTrader ni el archivo académico permiten acreditar el requisito fijo **6 productos CL NG GC HG ZC ZS × al menos dos vencimientos nativos elegibles × velas D1 completas 2012-01-01 → 2024-09-16 × primera publicación causal + licencia y costes**.

Este es un **NO-GO DE FUENTE para la misión de curva de futuros a presupuesto USD 0**, no una prueba económica negativa. **0 backtests; 0 Sharpe, PF o PnL; 0 nuevos traders certificados.** No inventar OHLCV para rellenar huecos. Ningún archivo de precios se incorporó al repositorio ni al artifact: reportar sólo metadatos y SHA de fuente.

## Cinco ZIP gratuitos de TurtleTrader — descarga efectiva y años de filas parseables

Portal: https://www.turtletrader.com/hpd/ . Los ZIP permiten descarga pública sin tarjeta. Los precios pertenecen a históricos distintos del período que necesitamos. Los archivos mantienen ficheros .TXT aparentemente separados por vencimiento; eso NO prueba por sí solo el contrato nativo adecuado, calendario as-of o derechos de redistribución.

| Instrumento | ZIP de origen | Miembros .txt | Primera fecha encontrada | Última fecha encontrada | Filas fechadas 2012–2024 |
|---|---|---:|---|---|---:|
| CL (WTI) | `https://www.turtletrader.com/cddata/cl.zip` | 235 | 1983-03-30 | 2000-01-20 | **0** |
| GC (oro) | `https://www.turtletrader.com/cddata/gc.zip` | 214 | 1974-12-31 | 2000-01-27 | **0** |
| HG (cobre) | `https://www.turtletrader.com/cddata/hg.zip` | 319 | 1970-01-05 | 2000-01-27 | **0** |
| ZC (maíz) | `https://www.turtletrader.com/cddata/c.zip` | 219 | 1970-01-05 | 1999-12-20 | **0** |
| ZS (soja) | `https://www.turtletrader.com/cddata/s.zip` | 302 | 1970-01-05 | 2000-01-14 | **0** |
| NG (gas natural) | no enlazado en la colección | N/A | N/A | N/A | **no verificable** |

Precisión metodológica: las fechas son máximos/mínimos de **filas con primera columna reconocida** por el analizador (235/201 CL, 214/183 GC, 319/218 HG, 219/150 ZC, 302/211 ZS archivos text con fechas parseables). No significa que se haya validado cada columna de OHLC ni que toda fila fuera parseable; la ausencia total de 2012–2024 en lo parseable y la estructura de nombres de contratos antiguos basta para **no aprobar** la fuente, no para afirmar que jamás existan datos más recientes fuera de esa colección. Los archivos ZIP se descargaron a memoria temporal del runner y **no se redistribuyen**.

SHA256 de archivo original ZIP:

```text
CL cl.zip  2dad131a21a37ec1f81291d1fee7707edf8367972300bff9be697c94f3d15f25
GC gc.zip  96292d22406bdcda93b30f995b9f531acfa1b6b7136fabc5ec69eb0e6453395a
HG hg.zip  afb4b071f848e43e66e31200770870e487f141598a5c973d93f0f146594ddfd0
ZC c.zip   29123fc772003e4f2a810fe08b0091c0dad730a04a087bc9edd1a4cf020d63f4
ZS s.zip   f7455a8b4024860610b2d0972b10c90803077e5382fc1bf1c6e9421b7f39f8f0
```

## Archivo académico SSEconomics — acceso confirmado pero NO velas D1

Repo: https://github.com/SSEconomics/commodity-spot-and-futures-data; archivo público `Futures Data.zip` descargado y verificado: **13,487,150 bytes**, **17 ficheros .xlsx**; incluye `wtifuturesdata.xlsx`, `henryhubfuturesdata.xlsx`, `goldfuturesdata.xlsx`, `copperfuturesdata.xlsx`, `cornfuturesdata.xlsx`, `soybeansfuturesdata.xlsx`.

SHA256: `a1e91345a6a131a0f30f6944edc07dabc065c9f671b36c283fdbff5d307361c3`.

El README del autor declara observaciones **de fin de mes / promedios mensuales y series mixtas**, curva por **horizonte de entrega**, y archivo **hasta diciembre de 2022**. Es material útil para comprender términos de estructura de futuros, pero **no verifica** velas diarias OHLCV de contrato nativo con identidad, calendario, primera publicación, coste ni 2023–2024. El origen Bloomberg de parte de los materiales exige verificar condiciones de reutilización antes de copiar raw a otros sistemas. No inferir licencia libre porque el ZIP sea públicamente descargable. **No hacer backtest con este archivo como si fueran 6×2 contratos diarios 2012–2024.**

## Otras vías gratuitas examinadas — NO rellenan la fuente

- https://github.com/axb0306/cme-futures-ohlc: carpetas CL/NG/GC/HG/ZC/ZS con OHLCV públicos de TopstepX, pero README y nombres muestran sobre todo 2025–26, no historia 2012–2024 de vencimientos nativos identificados; tampoco autoriza automáticamente reutilización de precios derivados de broker en otro sistema. **INCOMPATIBLE** con esta misión aunque sea buen ejemplo de formato.
- https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm: CFTC publica datos oficiales **semanales de posiciones** con historia larga. Eso no es OHLCV ni liquidaciones por contrato, y con lag de publicación requiere preregistro distinto. No usarlo para inventar velas.
- https://www.cmegroup.com/market-data/daily-bulletin.html: Daily Bulletin expone tablas oficiales de sesión previa, pero la página enlaza el **historical** a DataMine con requisitos de licencia; la vista de ayer no demuestra archivo gratuito 2012–24. No emplear web pública como repositorio masivo sin licencia.
- https://databento.com/futures: **USD 125 es crédito promocional de cuenta nueva, NO obligación de pagar USD 125**. No obstante cuenta/tarjeta/posibles cargos/entitlement no están habilitados ni aprobados; el usuario no tiene presupuesto. Regla actual USD 0 significa **NO abrir adquisición automática**, ni depósito ni garantizar crédito suficiente.

## Lo que sí existe

1. **Dos preflights de archivo público completados en GitHub Actions**: [#38342546391](https://github.com/mezas3238-hue/qore-core/actions/runs/38342546391), [#38342603409](https://github.com/mezas3238-hue/qore-core/actions/runs/38342603409). Segunda pasada fecha-fila acredita carácter antiguo de los cinco Turtle.
2. **18 tests estrictamente sintéticos PASS** de estructura, as-of settle/OI, fecha real de aviso vs cutoff broker, precios negativos WTI; [Actions #38341020091](https://github.com/mezas3238-hue/qore-core/actions/runs/38341020091).
3. Infraestructura trader lab + código de auditoría reutilizables para cuando exista fuente legítima. Fuente financiera comerciable aún **no certificada**.

## Gobernanza de parada y camino legítimo

- **M0 termina como `BLOCKED_DATA_OR_LICENSE` en la restricción USD 0**. No abrir M1 backtest con SSEconomics mensual o TurtleTrader de 2000, no cambiar a 5 mercados omitiendo NG ni reducir arbitrariamente 12 años, no usar Yahoo `CL=F` sintético/backadjusted como forward curve.
- Solo reconsiderar M0 con **dato externo material nuevo**: acceso a proveedor contractual auténtico sin tarjeta/cargo autorizado o documentación de un archivo abierto con derechos y metadatos suficientes, sin consultar resultados económicos previos. No exigir al propietario que pague.
- Si el propietario modifica alcance/mercados/fechas o autoriza dinero en una misión distinta, deberá registrarse **nuevo contrato de fuente y preregistro** antes de cualquier PnL, no reinterpretar esta validación como ya aprobada.
- No se tocó LIVE, CIBO, Shared, QDLE, VPS, brokers, órdenes, MT5 ni el holdout del proyecto FX. Ninguna certificación por este gate.

**Dictamen de fuente: gratuito descargable ≠ completo ni licenciado ≠ señal rentable. El resultado de M0 es un bloqueo de datos, no de capacidad de QORE.**
