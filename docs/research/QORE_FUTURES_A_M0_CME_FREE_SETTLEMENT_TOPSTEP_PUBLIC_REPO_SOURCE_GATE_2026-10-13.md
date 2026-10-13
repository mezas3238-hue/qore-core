# QORE Futures A — M0 cero dólares: auditoría adicional CME + GitHub (13-oct-2026)

**DICTAMEN:** `BLOCKED_DATA_OR_LICENSE` para el universo fijo de seis futuros con contratos nativos, OHLCV diario por vencimiento y cobertura 2012–2024. Esta fase es **sólo fuente**, no backtest y no refutación de ningún edge. **Presupuesto: US$0.**

### Ejecución nueva independiente

- [Actions #38370080545](https://github.com/mezas3238-hue/qore-core/actions/runs/38370080545), **SUCCESS**, compromiso de fuente `aa3c0bf3233d4057637c41ab3d770e0f5c5511a3`.
- Script `.github/scripts/qore_futures_a_m0_public_vendor_eligibility_v1.py`; workflow `.github/workflows/qore-futures-a-m0-free-cme-gh-access.yml`.
- El runner consultó **sólo metadatos públicos**: listado de nombres de ficheros del repositorio `axb0306/cme-futures-ohlc` para seis roots y UN endpoint oficial de CME API indicado en su documentación; jamás descargó market prices, ni calculó Sharpe/PnL. Archivo JSON de evidencia en artifact del run, sin valores de mercados.

## Repositorio público de velas TopstepX — 6/6 raíces, 0/6 cumplen periodo

Origen: https://github.com/axb0306/cme-futures-ohlc . El autor publica barras OHLCV descargadas de TopstepX, con ocho temporalidades, pero **no documenta meses de vencimiento individuales en cada fila ni autorización CME de redistribución**. Inventario efectivo en GitHub API en este turno:

| Root | Primer día anunciado en archivo OHLCV D1 | Último día del archivo D1 | Cubre 2012–2024 |
|---|---|---|---|
| CL | 2025-06-02 | 2026-04-14 | **No** |
| NG | 2025-11-07 | 2026-03-27 | **No** |
| GC | 2025-03-24 | 2026-04-14 | **No** |
| HG | 2026-02-17 | 2026-04-14 | **No** |
| ZC | 2025-12-08 | 2026-04-14 | **No** |
| ZS | 2025-09-26 | 2026-04-14 | **No** |

Estos extremos son **fechas declaradas en nombres de fichero**, no fechas de todas las filas validadas. Aunque haya 1min para seis raíces, la ventana es igualmente reciente y **es una serie por símbolo/root**, no dos contratos mensuales nativos por día. Ni uno de los seis satisface histórico previo al corte de 2024-09-17. No importar ni hacer backtest para intentar rescatar la misión.

Otra fuente observada: [domzack/mgc-ohlcv-data](https://github.com/domzack/mgc-ohlcv-data) presenta velas de Micro Gold desde 2023-01, con **rollover dinámico de contrato de mayor volumen**, no dos vencimientos nativos simultáneos y sólo para oro. Tampoco encaja en 6×2 de esta misión.

## CME DataMine: verdad matizada de GRATUITO vs histórico comprable

1. [Aviso oficial CME de noviembre 2023](https://www.cmegroup.com/notices/electronic-trading/2023/11/20231120.html) distingue **Settlements File after midnight CT / fee-liable NO** de **End of Day File / fee-liable YES**. El aviso retrasó la migración efectiva del FTP al 1-abr-2024 ([enmienda CME](https://www.cmegroup.com/notices/clearing/2023/11/Chadv23-352.html)). **NO decir que CME cobra toda liquidación diaria**.
2. [CME documentación API](https://www.cmegroup.com/datamine/datamine-api.html) exige **OAuth o Basic Auth para todas las llamadas**, con permisos por fichero; [List API](https://www.cmegroup.com/datamine/datamine-list-api.html) también exige autenticación. Por su parte [FAQ de CME End of Market Summary](https://www.cmegroup.com/articles/faqs/access-to-cme-group-settlement-data-faq.html) detalla suscripciones desde ~US$105/mes, que **no deben confundirse** con el Settlements File postmedianoche sin fee de 2023.
3. Verificación ACTUAL del runner sin credenciales: **HTTP 401** al hacer llamada GET `headers_only=true` contra el ejemplo CME `20250625-EOD_XCBT_C_FUT_0_ETH_P`. **Este fid de ejemplo corresponde a EOD**, y su 401 comprueba rechazo de la API sin entitlement en nuestro entorno; NO es una prueba de que el archivo gratis Settlements File postmedianoche tenga coste ni de que un usuario autorizado no pueda acceder a él. **No existe CME API ID conectado ni dataset libre registrado para QORE en este estudio**.
4. **No se ha acreditado** que la colección de Settlements File gratis de 2024 en adelante incluya todo el histórico **2012–2024**, ni que incluya OHLCV (una liquidación es un precio, no una vela completa), ni que exponga dos vencimientos elegibles con todos los timestamps. Los enlaces de CME llevan a catálogo y alta/contrato; no exigir tarjeta ni gasto al propietario. No automatizar un scraping de endpoints autenticados ni crear un comprador.
5. **Oportunidad legítima futura SIN GARANTÍA:** si en algún momento existe usuario CME gratuito autorizado, y prueba de términos/licencia/retención y de cuota US$0, podríamos recopilar los **nuevos Settlements Files** legalmente a partir de ahora. Eso sería histórico prospectivo *desde su fecha de captura*, **NO reconstruiría retroactivamente el periodo preregistrado**. Tampoco produciría OHLCV sin fuente adicional.

## Relación con otras fuentes ya auditadas

El [informe principal](QORE_FUTURES_A_M0_FREE_ARCHIVE_6_SOURCE_EXECUTED_BLOCKED_2026-10-13.md) conserva la evidencia original de:
- TurtleTrader ZIP CL/GC/HG/ZC/ZS: filas con fecha parseable hasta 1999–2000 y **0 filas 2012–2024**. NG no en colección. Los cinco históricos antiguos no sirven.
- SSEconomics: 17 XLSX públicos cubriendo la curva de seis mercados hasta dic-2022; **serie mensual/mixta sin velas D1 nativas** ni licencia de redistribución Bloomberg demostrada.
- **US EIA**: cuatro series diarias reales gratuitas WTI/NG primer/segundo rango, 2012-01-03→**2024-04-05**, **12.352 observaciones**, no OHLCV ni contract expiry exacta ni timestamps de primera publicación. [Workflow exportado](https://github.com/mezas3238-hue/qore-core/actions/runs/38343102029), artifact #11786984830 para descarga manual durante retención; no interpretar como PnL real.

## Decisión de parada M0

**No hay dataset gratuito auditado que cumpla el contrato económico fijo 6×2, D1 OHLCV nativa por contract-month 2012–sep2024, EOD as-of y costes de ejecución.** Continuar mirando nuevos nombres de proveedor sin nueva información material arriesgaría una búsqueda indefinida; por tanto, **se cierra la ronda de fuentes actuales como BLOCKED, no como NO_SUPPORT**. Documentos, scripts y resultados se conservan en el PR #895 SIN MERGE; el bloqueante es dato/derecho, no código del laboratorio.

No hacer test económico sobre solo oro 2023–26, el archivo TopstepX 2025–26, los EIA front-rank sin identity, Turtle hasta 2000 ni curva académica mensual como si fueran futuros nativos transables. No rebajar selección del universo original ni tocar 2024-09-17+ holdout de QORE Native, MT5, brokers, LIVE, CIBO, Shared, QDLE o VPS. No inferir rentabilidad ni nuevos certificados: **0/3 traders**.

**Criterio para reabrir:** fuente nueva con propiedad legal verificable, historiales nativos completos y coste auténticamente cero, o **nuevo mandato explícito** que cambie universo/ventana/presupuesto con preregistro propio. Ninguna compra implícita por decir «avanza».
