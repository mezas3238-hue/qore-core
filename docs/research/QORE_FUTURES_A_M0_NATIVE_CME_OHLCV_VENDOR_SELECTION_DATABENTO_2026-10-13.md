# QORE FUTURES A / M0 — fuente preferida para VELAS reales: Databento CME GLBX.MDP3

**Fecha de verificación pública:** 13 octubre 2026. **Estatus**: PROVEEDOR EN CATÁLOGO, **SIN cuenta / entitlement / API key / dataset privado verificado**, cero compras, cero velas auténticas descargadas al proyecto, cero PnL. [Misión issue #894](https://github.com/mezas3238-hue/qore-core/issues/894), [PR #895](https://github.com/mezas3238-hue/qore-core/pull/895). No tocar investigación FX Native cerrada.

## Selección de proveedor, por compatibilidad antes de señales

**Candidato preferido: Databento [Futures](https://databento.com/futures) dataset `GLBX.MDP3`**: documentación oficial declara cobertura de CME/CBOT/NYMEX/COMEX **desde junio 2010**, y esquemas `ohlcv-1d`, `ohlcv-1m`, `definition`, `statistics`, `mbp-1`/trades. La cobertura general del feed NO prueba que cada vencimiento de los seis productos tenga exactamente todos los campos de 2012–2024; certificarlo con snapshot genuino por contrato. Docs: https://databento.com/docs/knowledge-base/datasets , https://databento.com/docs/schemas-and-data-formats/ohlcv , https://databento.com/docs/schemas-and-data-formats/statistics , https://databento.com/docs/examples/futures/retrieving-oi-and-settlement-prices , https://databento.com/docs/schemas-and-data-formats/whats-a-schema .

**OHLCV-1d** son barras de **transacciones electrónicas agregadas de medianoche UTC a medianoche UTC**; NO coinciden siempre con trading-day oficial CME ni con precio de liquidación. La pendiente causal para el modelo futuro debe usar **`statistics` official settle + volumen+ OI** y `definition` nativa con `ts_recv`/tiempo de publicación; adquirir `ohlcv-1d` solo como candles de trading, no confundir `close` de transacciones con `settlement`. Los OI de CME suelen publicarse **UTC día siguiente**; el backtest no debe mirar OI antes de entonces. Si deseamos sesiones CT se debe derivar OHLCV D1 por trading session a partir de OHLCV-1m/trades, porque el diario Databento es UTC. Desde 2010 pre2017 hubo protocolo histórico FIX/FAST y desde 2017 MDP3; validar precisión histórica de forma separada.

**No descargar `ALL_SYMBOLS` ni todos los MBO ticks.** Uso `stype_in="parent"` y símbolo base `CL.FUT`, `NG.FUT`, `GC.FUT`, `HG.FUT`, `ZC.FUT`, `ZS.FUT`; ese tipo parent agrupa los futuros individuales de un root, por lo que debe recortarse a los vencimientos elegibles tras consultar `definition`; no usar `CL.n.0`/continuous como precio PnL ni series backadjusted. Empezar solo con 5 sesiones 2012, 2020 (negativo WTI), y 2024 anteriores a 2024-09-17, 2 vencimientos por root y `definition/statistics/ohlcv-1d`, si disponibles.

**Costo no se adivina:** Databento permite presupuesto sin descarga con API `Historical.metadata.get_cost(dataset="GLBX.MDP3", stype_in="parent", symbols=["CL.FUT"], schema="ohlcv-1d", start="2012-06-01", end="2012-07-01")`. Consultar el costo de tres esquemas para los seis roots y del horizonte 2012-01→2024-09-16 antes de pedir nada; `definition` requiere rangos discretos días enteros. [Databento get_cost](https://databento.com/docs/api-reference-historical), [Pricing](https://databento.com/docs/faqs/usage-pricing-and-data-credits). Databento publica **$125 crédito gratis** a cuentas nuevas sujeto a condiciones y vencimiento, no afirmar que cubrirá 12 años ni tasas/licencias extras. `metadata.get_cost` es sin cargo, pero las descargas históricas sí pueden facturarse. Solo ejecutar descarga tras confirmar por usuario créditos disponibles, tipo de licencia, costo exacto y techo de gasto.

## Alternativas si acceso/límites no se cumplen

- **CME DataMine** https://www.cmegroup.com/datamine.html — exchange origin, datasets `Settlements` y `End of Market Summary` de contratos; [FAQ](https://www.cmegroup.com/articles/faqs/access-to-cme-group-settlement-data-faq.html) publicación de web/archivos hasta medianoche CT. Pedir SKU concreto de contract EOD nativo, no comprar solo *Continuous Price Series*, no garantizar OHLCV completo por settlement archive.
- **Barchart OnDemand** https://www.barchart.com/ondemand/api/getHistory — `type=daily` o `minutes`, campo volume por contrato y openInterest donde aplique. Pedir prueba de vencimientos históricos concretos y derechos de investigación; dailyNearest/dailyContinue y backAdjust no son curvas nativas de ejecución.

## Protocolo piloto M0 → un gate, cero PnL

**Gate 0A presupuesto fuente:** autoridad de acceso con API Key gestionada como secret privado, ningún token en chats/commits. Preguntar al proveedor/portal costo total de `definition`, `statistics`, `ohlcv-1d` para seis roots 2012–2024 con top dos contratos elegibles, si 2012 no está disponible por root o un campo crítico está ausente NO silencioso downgrade.

**Gate 0B muestreo causal:** snapshots reales ~5 sesiones en 2012, abril 2020, agosto 2024 por root; conservar `instrument_id, raw_symbol, exchange, expiry, trade date, price, publication/recv times` bajo contrato licenciado y SHA256; validar overnight roll/day session, serie continua vs native, settlement distinto close, spread front-next, volumen/OI publicado tarde y CL-2020 precios negativos. No publicar precios raw al repositorio.

**Gate 0C reproducibilidad:** fuente de especificación vigente `first_notice, last_trade, broker_exit_cutoff, tick_size,multiplier`; costos broker/clearing/exchange, spread/slippage (MBP1/BBO o proxy validado). Guardar contrato firmado/permisos fuera GitHub. Tras los tres, decidir `SOURCE_READY_FOR_PREREG` o `BLOCKED_DATA_OR_LICENSE` de una vez. El checker sintético existente en [PR #895](https://github.com/mezas3238-hue/qore-core/pull/895) **NO** autoriza GO por sí solo.

## Ejemplo seguro: sólo pedir ESTIMACIÓN, sin descarga ni PnL

```python
import os
import databento as db

# Poner DATABENTO_API_KEY en variable de entorno local/secret, NUNCA en GitHub.
client = db.Historical(os.environ["DATABENTO_API_KEY"])
for root in ["CL", "NG", "GC", "HG", "ZC", "ZS"]:
    parent = f"{root}.FUT"
    for schema in ["ohlcv-1d", "statistics", "definition"]:
        cost = client.metadata.get_cost(
            dataset="GLBX.MDP3",
            symbols=[parent],
            stype_in="parent",
            schema=schema,
            start="2012-06-01",
            end="2012-06-06",
        )
        print(root, schema, f"quoted_usd={cost:.4f}")
```

**El script anterior consulta sólo metadatos y no ejecuta `get_range`, `batch.submit_job` ni descargas.** Si el proveedor rechaza un esquema/cobertura, registrar sin sustituciones. No puede operar sin cuenta/API key legítimas.

## Decisión actual

**Fuente preferente Databento, respaldo CME DataMine, alternativa Barchart. Presupuesto autorizado $0. Aún NO existe acceso ni velas auténticas en QORE Futures A.** Comenzar con D1 contract-native + settlement/volume/OI y definiciones; M1 sólo si una hipótesis intradía futura distinta lo requiere. El cierre QORE Native ADR #893 sigue en vigor; 0/3 nuevos traders certificados. `SOURCE_READY_FOR_PREREG=False`.
