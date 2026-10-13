# QORE Futures A M0 — Portara/CQG: identidad contractual verificada en catálogo, coste cero NO demostrado
**Fecha:** 2026-10-13. **Mandato:** fuente de históricos CME/CBOT/NYMEX/COMEX, 6 futuros (CL NG GC HG ZC ZS), dos vencimientos nativos, días 2012-01-01..2024-09-16, D1 OHLCV+settlement+OI, presupuesto propietario **USD 0**. **Sin operaciones ni backtests económicos**.

## Qué se puede acreditar y qué NO

Portara publica [históricos diarios de contratos](https://portaracqg.com/historical-daily-futures-data/) con la posibilidad contractual de escoger **individual contract files** y columnas **date, open, high, low, settlement, volume, openInterest**. Dispone también de `lastPrice` separado de `settlement`, por lo cual un EOD trade close NO debe equipararse automáticamente al settlement. El catálogo afirma historia antigua y archivos separados por expiración para estos seis productos. **Esto es evidencia de disponibilidad comercial de un formato potencialmente adecuado, no prueba de que los bytes 2012–2024 estén disponibles gratuitamente a QORE ni de permisos de explotación.**

| root CME | producto | Portara alias catalogado | página de datos diarios con muestra | observación |
|---|---|---|---|---|
| CL / NYMEX | WTI oil | CLA (Combined) | https://portaracqg.com/futures/day/cla/ | contrato nativo como `CLA2026F`, diaria desde 1983 |
| NG / NYMEX | Henry Hub nat gas | NGA (Combined) | https://portaracqg.com/futures/day/nga/ | datos de futuros por vencimiento; diaria desde 1990 según catálogo |
| GC / COMEX | Gold | GCA (Combined) | https://portaracqg.com/futures/day/gca/ | datos de futuros por vencimiento; diaria desde 1974 según catálogo |
| HG / COMEX | Copper | CPA (Combined) | https://portaracqg.com/futures/day/cpa/ | contrato alias CPA/HG, diaria desde 1972 |
| ZC / CBOT | Corn | CNA (Combined) | https://portaracqg.com/futures/day/cna/ | **precio publicado $180 USD** por last-30-years daily individual (observación 2026-10-13, verificar antes de ordenar) |
| ZS / CBOT | Soybeans | SSA (Combined) | https://portaracqg.com/futures/day/ssa/ | datos diarios antiguos por vencimiento |

**Regla de identidad**: mapear los alias de proveedor `CLA/NGA/GCA/CPA/CNA/SSA` a exchange `CL/NG/GC/HG/ZC/ZS` **solo** si el contrato por año/mes y reglas de roll/lot/quote han sido confrontados con specs oficiales vigentes para ese período. Alias `GCA` o `CPA` puede indicar *combined/pit+globex*, y por tanto **no equivale necesariamente al feed MDP3 Globex exclusivo**. Mantener flags de venue/session exactos y no asumir que un split histórico se conserva sin ajustes.

### Límite real del acceso gratis

- [El proveedor ofrece muestras gratuitas descargables](https://portaracqg.com/sample-data/), incluso de contratos individuales; esos ejemplos **no equivalen** a una licencia universal para descargar todos los días de 2012 a 2024.
- [Portara Downloader](https://portara.net/) anuncia una **Free Tier**, pero **no publica límites/entitlements suficientes para demostrar que incluya 6×2 contratos completos de 2012–2024 ni ausencia de tarjeta/cargos**. No registrar como FULL FREE bajo mera publicidad de “Free Tier”.
- [Portara CLA](https://portaracqg.com/futures/day/cla/) dice que la entrega de data dump individual ocurre **después de realizar un pago**, con reglas y formatos personalizados. [Portara CNA](https://portaracqg.com/futures/day/cna/) publica $180 por último período de 30 años de contratos individuales diarios; no extrapolar ese importe a toda la cartera de seis ni mezclar con una cotización formal.
- Una muestra individual sería admisible para **verificar formato y esquema** con permiso; no sería admisible como evidencia de cobertura ni autorización de PnL de seis activos. No se ha descargado ninguna muestra en QORE porque no arreglaría el faltante estructural sin derechos/licencia y podríamos exponer material de terceros sin necesidad.
- **Presupuesto $0, cuenta/entitlement no conectados, compra NO ejecutada**. Fecha de primera publicación histórica (as-of), exact historical expiry, roll y costos deben probarse en una licencia real; ficha comercial no los certifica.

## Fuentes gratuitas ejecutadas anteriormente (NO-GO)

Conservar [auditoría FREE ZIP+EIA ejecutada](QORE_FUTURES_A_M0_FREE_ARCHIVE_6_SOURCE_EXECUTED_BLOCKED_2026-10-13.md): TurtleTrader ZIP para cinco productos hasta 1999/2000; SSEconomics 17 XLSX curvas mensuales/mixtas hasta 2022; **EIA 12.352 observaciones gratuitas WTI/NG rank1/2** del 2012-01-03 a 2024-04-05, **sin barras OHLC ni identidad de vencimiento**. [Auditoría pública CME+Topstep](QORE_FUTURES_A_M0_CME_FREE_SETTLEMENT_TOPSTEP_PUBLIC_REPO_SOURCE_GATE_2026-10-13.md): OHLCV GH recientes 2025–26, no 2012–24; API CME EOD devuelve 401 sin credenciales, sin demostrar coste del Settlements File postmedianoche.

## Decisión y frontera del trabajo

**M0 = `BLOCKED_DATA_OR_LICENSE`** (especificación 6×2 2012–2024, cuenta del usuario $0): **NO demuestra inexistencia de edge**. Portara aporta evidencia nueva de proveedor con **schema contractual correcto**, pero no material nuevo de datos gratis descargables *completos*. No abrir pruebas PnL; no cambiar universo a 2 o 5 roots; no intentar bypass de compra/captcha/cuenta. Si un tercero aporta por una vía lícita el entitlement/documentación y los archivos, el checker de M0 ya está en PR #895. No gastar dinero ni comprometer una compra por iniciativa propia.

**Criterio único de avance:** licencia válida + archivos nativos D1 2012–2024 6×2 y primeros timestamps de disponibilidad + fuentes de costes reales y delivery terms; de lo contrario STOP. Aceptar “muestra” solo como evidencia de formato, NO source ready.

**Estado de certificación:** **0/3 nuevos traders, holdout intacto, NO economic PnL, NO LIVE/Shared/CIBO/VPS/MT5/QDLE**, rama investigación QORE Futures A independiente del cierre científico de FX Native ADR #893.
