# QORE Futures A — M0 costo cero: auditoría económica de fuentes gratuitas, NO PnL

**Fecha:** 2026-10-13 UTC. **Presupuesto:** USD 0, sin tarjeta, sin API key, sin broker; no se abrió holdout ni se ejecutó PnL. **Autoridad de esta ronda**: [issue #894](https://github.com/mezas3238-hue/qore-core/issues/894) y [PR #895](https://github.com/mezas3238-hue/qore-core/pull/895). EVIDENCIA reproducible: [GitHub Action #38342722003](https://github.com/mezas3238-hue/qore-core/actions/runs/38342722003), workflow `.github/workflows/qore-futures-a-m0-free-zero-budget-source-inventory.yml`, SHA de fuente `2f6da032f95e946c0f4fa68023def2fe1201756e`. **No se copiaron los datos ZIP al GitHub repo; se conservaron únicamente metadatos/hashes y conteos de registros.**

## 1. TurtleTrader gratuito: 5 ZIP realmente descargados; DESCARTADOS para ventana 2012–2024

Se descargaron públicamente cinco ZIP de [https://www.turtletrader.com/hpd/](https://www.turtletrader.com/hpd/) sin registro. Se recorrieron registros reales de fecha en archivos de contratos, resolviendo fecha **YYMMDD** (cada TXT incluye OHLC, volumen, OI; distinto de archivos sintéticos continuos) y se obtuvieron estos extremos **min y max observados**, que no implican completitud diaria ni calidad de precio.

| Producto QORE | ZIP, archivos TXT | mínimo en filas | máximo en filas | SHA256 del ZIP original |
|---|---:|---|---|---|
| CL | 235 | 1983-03-30 | 2000-01-20 | `2dad131a21a37ec1f81291d1fee7707edf8367972300bff9be697c94f3d15f25` |
| GC | 214 | 1974-12-31 | 2000-01-27 | `96292d22406bdcda93b30f995b9f531acfa1b6b7136fabc5ec69eb0e6453395a` |
| HG | 319 | 1959-07-01 | 2000-01-27 | `afb4b071f848e43e66e31200770870e487f141598a5c973d93f0f146594ddfd0` |
| ZC (archivo `c.zip`) | 219 | 1959-07-01 | 1999-12-20 | `29123fc772003e4f2a810fe08b0091c0dad730a04a087bc9edd1a4cf020d63f4` |
| ZS (archivo `s.zip`) | 302 | 1959-07-01 | 2000-01-14 | `f7455a8b4024860610b2d0972b10c90803077e5382fc1bf1c6e9421b7f39f8f0` |

Gas natural NG **no figura** entre las descargas gratuitas visibles de ese portal; la guía histórica PDF menciona el símbolo como posible contrato en un CD, pero no da enlace ZIP público NG, así que no suponer datos recibidos.

**DICTAMEN fuente Turtle:** `NOT_USABLE_FOR_2012_2024` para los seis. Aunque el usuario puede abrir los ZIP libremente, el footer [turtletrader.com/hpd](https://www.turtletrader.com/hpd/) dice 'all rights reserved' y que para copiar/redistribuir requiere permiso; no republicar archivos íntegros. La simple disponibilidad pública no otorga licencia universal.

**Nota operativa:** imposible re-etiquetar estos archivos como 2012-2024, fabricando contratos o extrapolando retornos. Podrían existir datos históricos 1959–2000 valiosos para enseñanza, pero fuera de mandato actual; no nueva estrategia.

## 2. Archivo académico SSEconomics: físicamente recibido, 17 XLSX; no son velas D1 certificables

Fuente: [SSEconomics/commodity-spot-and-futures-data](https://github.com/SSEconomics/commodity-spot-and-futures-data); [GitHub Action #38342722003](https://github.com/mezas3238-hue/qore-core/actions/runs/38342722003). ZIP `Futures Data.zip`: **13,487,150 bytes**, 17 archivos XLSX por commodity, SHA256 `a1e91345a6a131a0f30f6944edc07dabc065c9f671b36c283fdbff5d307361c3`; commodities de interés están en el paquete. Readme indica información histórica **hasta diciembre 2022** con precios por horizonte de entrega y agregaciones mayormente mensuales/fin de mes, no OHLCV D1 nativo por vencimiento ni timestamps de primera publicación. El repositorio **no anuncia licencia SPDX**, el origen incluye Bloomberg; no autorizar redistribución ni uso comercial sin comprobar derechos. Puede servir solo para entender geometría de curva sin PnL.

## 3. Nueva fuente gubernamental gratuita plausible: U.S. EIA, CURVA DE ENERGÍA D1 (NO OHLCV)

**Fuentes primarias oficiales:**

- WTI Cushing 1º futuro [RCLC1D](https://www.eia.gov/dnav/pet/hist/RCLC1D.htm), 2º futuro [RCLC2D](https://www.eia.gov/dnav/pet/hist/RCLC2D.htm); cobertura visible desde 1983 (1º) y 1985 (2º) y años 2012–2024.
- Gas natural Henry Hub 1º futuro [RNGC1D](https://www.eia.gov/dnav/ng/hist/rngc1d.htm), 2º futuro [RNGC2D](https://www.eia.gov/dnav/ng/hist/rngc2d.htm); [EIA indica explícitamente que cesó publicar datos NG futures **después del 5 de abril de 2024**](https://www.eia.gov/dnav/ng/ng_pri_fut_s1_m.htm).

Cuatro archivos XLS oficiales `https://www.eia.gov/dnav/pet/hist_xls/RCLC1d.xls`, `.../RCLC2d.xls`, `https://www.eia.gov/dnav/ng/hist_xls/RNGC1d.xls`, `.../RNGC2d.xls`. Se inició [Actions #38342875054](https://github.com/mezas3238-hue/qore-core/actions/runs/38342875054) para verificar descarga real y estructura (sin pago, sin token), no suponer que éxito significa certificado antes de ver logs.

**Clasificación:** `SOURCE_CANDIDATE_PUBLIC_ENERGY_FRONT2_DAILY_REFERENCE_PRICES`. No hay 4 valores OHLC para cada día: son precios diarios de fin de jornada/settlement según definición EIA, y **futuro 1/2 son tenores móviles**, no IDs de contratos exactos. Pueden apoyar análisis no-económico preliminar de la forma de curva o relación contango/backwardation, **NO** permiten reconstruir roll, bid/ask, spreads de ejecución, costes de margin, OI por pata, publicación PIT ni PnL auténtico de futuros físicos. En particular, NG se interrumpe anticipadamente en 2024, por tanto no satisface la cobertura original hasta 2024-09-16.

## 4. Otras fuentes descartadas para cumplir esta misión con USD 0

- [axb0306/cme-futures-ohlc](https://github.com/axb0306/cme-futures-ohlc) publica diariamente CSV de seis roots desde fechas principalmente **2025–2026**, no evidencia 2012–2024 ni contratos nativos individuales; no licencia SPDX en repositorio.
- [Databento](https://databento.com) USD125 = crédito para cuenta nueva, **no cuota de admisión**, pero exige normalmente tarjeta / posible cargo por excedente; el usuario NO tiene presupuesto ni ha autorizado datos de pago.
- [CME DataMine](https://www.cmegroup.com/datamine.html) idealmente es fuente oficial licenciada pero su disponibilidad comercial no implica acceso gratuito.

## 5. Gate de decisión sin falsificar source readiness

**Resultados comprobados:**
1. Cinco ZIP históricos auténticos gratuitos 1959/1983–2000 descargados, hashes custodios; **fallan cobertura 2012–24**.
2. ZIP académico gratuito 17 commodities descargado, 13.49 MB, **falla D1 OHLCV native 2012–24, licencia aún ambigua**.
3. Datos oficiales EIA WTI+NG front1/front2 diarios identificados (acceso XLS pendiente de verificar en CI); cubren parcial del universo y no son OHLC ni IDs nativos.

**Decisión para misión completa de seis productos:** `SOURCE_READY_FOR_PREREG=False` y `M0_BLOCKED_FOR_FULL_SIX_ROOTS_UNDER_USD0`, a menos que aparezcan fuentes gratuitas realmente equivalentes con derechos/cobertura y costes. **No extrapolar este NO-GO a inexistencia de edge**, ni evaluar económicamente la hipótesis de curva.

**Única vía de valor sin gasto:** completar la revisión no-económica de la fuente EIA en un subalcance WTI y NG, guardando precios solo si copyright/legal lo permite, y no llamarla entrenamiento/certificación. No cambiar alcance a escondidas ni investigar estrategias sin autorización explícita. 0/3 QORE Native; no tocar LIVE, broker, VPS, MT5, CIBO, Shared, QDLE ni FX holdout.
