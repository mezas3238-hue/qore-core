# QORE FUTURES A — Solicitud de información y cotización a proveedor de datos (RFI, borrador; NO enviada)

**Fecha:** 13 de octubre de 2026. **Mandato:** [Misión M0 #894](https://github.com/mezas3238-hue/qore-core/issues/894). Esta es una especificación para pedir oferta al proveedor; no es un contrato, presupuesto aprobado ni solicitud de compra. **No se ha enviado correo ni contactado CME.**

## Texto en inglés listo para proveedor / CME DataMine

**Subject: Historical contract-level EOD futures research data RFI — six CME commodity roots, 2012–2024**

We are evaluating a licensed historical dataset for private, non-redistributed quantitative research and would appreciate confirmation of exact dataset identifiers, coverage and pricing. **We are not ordering or approving any paid data in this inquiry.**

We require historical **individual tradable futures contracts (not continuous adjusted synthetic series)** for:

- NYMEX WTI Crude Oil `CL`
- NYMEX Henry Hub Natural Gas `NG`
- COMEX Gold `GC`
- COMEX Copper `HG`
- CBOT Corn `ZC`
- CBOT Soybeans `ZS`

Requested research period: **2012-01-01 through 2024-09-16, inclusive**, and at least the front two genuinely listed and eligible contract expirations for each product/trading date. We need every historical **individual contract ID, root, exchange, delivery month/year, exchange trade date, final daily settlement price, publication timestamp or conservative time-of-availability policy, daily traded volume and open interest with publication timing and revision status, exchange last trading date, first notice date when applicable, delivery notice, first delivery date, and contract multiplier/tick/quote convention with historical specification changes**.

Please identify which fields are included directly and which require an additional calendar/reference dataset. We cannot infer historical first-publication time from a retrospectively updated website page. We cannot use a back-adjusted continuous series for executable PnL. Please specify whether EOD data are **exchange actual settlements**, indicative marks when no trading occurred, and whether history includes the period around negative WTI settlements in April 2020 without censoring values.

Please provide **(1) exact licensed dataset name(s), (2) years and symbol coverage, (3) downloadable sample of a small date/symbol window and format schema, (4) licensing terms for internal research, storage, retention, allowed derived summaries and whether public SHA metadata are permissible, (5) total one-time cost for the requested period and six products or month-by-month alternative, plus any additional rights and delivery/API costs, and (6) any restrictions on paper execution, professional account access or historical-data redistribution**.

We will assess the sample solely for metadata, reproducibility and correctness before requesting purchasing approval. No credentials or confidential prices will be placed in public GitHub.

## Cuestionario de decisión interna: una ronda, GO/NO-GO

| Dependencia | Estatus comprobado | Condición de aprobación |
|---|---|---|
| Histórico nativo por contrato de 6 mercados | **NO ENTREGADO** | 2012-01-01..2024-09-16, 2 vencimientos reales elegibles en días relevantes |
| CME DataMine catálogo ofrece settlements | **SÍ — CANDIDATO OFICIAL** | SKU/archivo exacto y sample adquirido en proceso autorizado |
| Calendario último día / notices / entrega | **DATOS DE REFERENCIA OFICIALES VISIBLES PARCIALMENTE** | versiones históricas completas y cutoff de liquidación broker |
| Timestamp as-of publicaciones EOD / OI | **NO HOMOLOGADO** | evitar usar settlement u OI de día d en decisión anterior a publicación |
| Cotización completa seis productos | **NO COTIZADO** | presupuesto real por escrito; aprobación del propietario |
| Licencia de investigación privada | **NO VERIFICADA** | entitlement / receipts y autorización de retención |
| Costos exchange + broker + clearing + spread/slippage | **NO RECIBIDOS** | estimación ejecutable y fuente broker elegida |
| Serie continua versus contratos nativos | **NO ACEPTAR CONTINUOUS PARA PNL** | native delivery-month + contract IDs / settlement facts por contrato |
| Resultado económico de trading | **NO EXISTE** | prohibido hasta comprar/autenticar fuente y preregister una sola hipótesis |

**Estado a la fecha:** `M0_SOURCE_NOT_YET_ACQUIRED`; presupuesto autorizado de compra 0 USD, no es afirmación de que el proveedor no tenga datos. Si la oferta no cubre los criterios, cerrar M0 `BLOCKED_DATA_OR_LICENSE` en lugar de buscar decenas de proveedores/proxies.

Fuentes de referencia: [CME DataMine](https://www.cmegroup.com/datamine.html), [CME Settlement FAQ](https://www.cmegroup.com/articles/faqs/access-to-cme-group-settlement-data-faq.html), [CME clearing calendar ejemplo CL/NG](https://www.cmegroup.com/content/dam/cmegroup/notices/clearing/2026/05/chadv26-192.pdf), [CFTC CL negative 20-abril-2020](https://www.cftc.gov/PressRoom/PressReleases/8315-20). Otra fuente posible CFTC COT/USDA WASDE *no está dentro* del primer test de curva.
