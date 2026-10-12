# QORE Native — G1-PRE BID/ASK native tick source integrity (continuación) — 2026-10-12

**Parent immutable:** commit `ba64abffd8f74d8c1b5975014234790f4b3e6543`, handoff 33×7. **Alcance:** contrato y tests de *formato/causalidad* para ingestión posterior de pares BID/ASK. No se incorporaron quotes reales nuevas, no hay backtest NET, ni PAPER, ni cambios a producción. Mantener `0/3` traders certificados.

## Diagnóstico de datos heredados

- G0 33/33: **24.377.420 barras M5**, no contienen evidencia suficiente para atribuir spread histórico, fills ni comisiones a cada orden.
- Las tres screenshots del usuario contienen 33 pares BID/ASK **spot sin fecha/terminal/contrato homologados**, con spread cero GBPUSD y alias índice NDX100 y SPX500 sin equivalencia; **no son historia de ticks**.
- El test E2 231×foto en Actions #38266242429 (5 celdas sobre una foto de spread en dos ventanas) es una ilustración **no** ventaja NET.
- Existe una vía parcial diferente: [PR #803](https://github.com/mezas3238-hue/qore-core/pull/803), EURUSD ticks BID/ASK cTrader DEMO en **12 ventanas de 30 minutos escogidas en 2015–2026**, autenticación dual; **no es serie histórica completa 33×2016–2024, ni verifica que sus cuentas sean equivalentes a G0**. Reutilizar su lógica de autorización/captura *solo tras* comprobar Actions y cobertura real. [PR #835](https://github.com/mezas3238-hue/qore-core/pull/835) recoge M1, **no** sustituye BID/ASK.

## Implementación nueva

- `src/qore/infrastructure/trader_lab/qore_native_g1_pre_quote_source_gate_v1.py`: examina manifiesto declarado + **bytes exactos** de JSONL hash SHA256, lista explícita de instrumentos, símbolos congelados, tick size, precio decimal, orden de secuencia, marcas UTC `Z`, ausencia de cotizaciones futuras en decisiones as-of, causalidad de recepción en captura *forward*, y anomalías zero/cross/stale en cuarentena.
- `tests/infrastructure/trader_lab/test_qore_native_g1_pre_quote_source_gate_v1.py`: escenarios **enteramente sintéticos**, positivos y negativos. No prueban acceso al broker, calidad del dataset ni rendimiento.
- `.github/workflows/qore-native-g1-pre-quote-source-gate.yml`: CI **sin credenciales** y sin descargas, con Ruff/Pytest.

Formato de entrada: manifiesto JSON con identidad `QORE_NATIVE_G1_PRE_ASOF_QUOTE_PILOT_INPUT_V1`, `g0_source_sha256`, `provider=CTRADER_OPEN_API`, `environment=DEMO`, `source_kind=NATIVE_SIDE_TICKS_PAIRED_ASOF`, `timestamp_timezone=UTC`, `capture_mode=HISTORICAL_BACKFILL|FORWARD_PAPER_CAPTURE`, `broker_name`, `broker_server`, `account_fingerprint_sha256` (hash, nunca token), `quotes_jsonl_sha256`, `historical_NET_economics_claimed=false`, `production_enabled=false`, y `instruments` (1–33 entries) con `canonical_symbol`, `provider_symbol`, `provider_symbol_id`, `tick_size`, `broker_contract_document_sha256`. El digest documental aislado NO demuestra homologación.

Cada fila JSONL contiene `canonical_symbol`, `provider_symbol`, `provider_symbol_id`, `source_sequence`, `decision_time_utc`, `bid_market_time_utc`, `ask_market_time_utc`, `both_sides_received_at_utc`, `bid` y `ask`; para histórico el campo recepción debe ser `null`: no fabricar timestamp de recepción visto retrospectivamente. En captura prospectiva ambos lados deben haberse recibido antes de decidir. `decision_time_utc` es el tiempo de evaluación de la foto ensamblada, no una orden.

**PRECAUCIÓN técnica:** cTrader histórico obtiene ticks BID y ASK por lado: `NATIVE_SIDE_TICKS_PAIRED_ASOF` exige un adaptador verificable que reconstruya por orden temporal *last-known-bid + last-known-ask*, sin mirar el siguiente tick para rellenar valores y sin alterar el orden. Este gate solo inspecciona el JSONL resultante y **no verifica los ticks originales**, ni demuestra que el join fuera causal. Ese auditor *independiente*, su SHA de streams BID/ASK nativos y los offsets/latencias de su reloj son trabajo P0 obligatorio.

El umbral de stale as-of **5 segundos** es una política de **cuarentena de formato de piloto**, NO estimación de volatilidad, fill ni calendario de mercado. Quotes con bid=ask, bid>ask, o un lado anterior a 5s no se convierten en spread 0 ni coste válido. Fuente exhaustiva para operación requiere entradas y salidas separadas; una ventana de 30min de EURUSD no sostiene NET durante ocho años.

## P0 real no terminado y orden de ejecución

1. Recuperar run/artifacts de PR #803; verificar auth DEMO, BID y ASK separados, completitud `hasMore`, SHA por lado, timestamps originales, faltantes y broker exacto. Si falla, declarar `HISTORICAL_TICKS_UNAVAILABLE` y pasar a captura forward paper **sin enviar órdenes**.
2. Investigar **factibilidad de cobertura** por cuenta/contrato/costo de obtención antes de capturar 33×años: piloto **EURUSD** únicamente por disponibilidad de código preregistrado; no por PnL. Guardar sharding por semana/mes con SHA individual y testigos de huecos/mantenimiento; no inferir cierre por feed vacío.
3. Validar cTrader symbols/IDs de las **12 fuentes originales** frente a **21 fuentes IC Markets DEMO**, app y ticks; bloqueos explícitos `NAS100/NDX100/USTEC`, `SP500/SPX500/US500` y `GBPUSD` anomalía spot. Verificar FX lot sizes, tick/pip value, índices CFD size, spreads, comisiones, swap as-of.
4. Construir join as-of usando fuentes bid/ask nativas por lado, no interpolación ni futuro; modelar diferenciación de timestamp de evento, entrega y reloj, latencia medible y anomalías; someter datos sellados a gate externo independiente antes de economía.
5. Solo con cobertura temporal de entradas y salidas, contratos homologados, comisión RT, slippage, swap, horarios y NEWS PIT se habilita planificación de backtest NET y registro ex ante; no abrir holdout 2024-09-17+ para elegir ganadores.

## Dictamen de esta continuación

**Se instrumentó puerta de integridad de fuente y pruebas sintéticas.** No afirmar que hubo descarga/ejecución real sin workflow verde y artefactos. `G0_33_PASS`; `E2_E3_NO_POSITIVE_SUPPORT`; `G1_HISTORICAL_NET_BLOCKED`; `CERTIFIED_0_OF_3`. Prohibido activar VPS, MT5, LIVE, CIBO, Shared y QDLE.


## P0.2 — Reconstrucción independiente as-of de streams normalizados (módulo añadido)

Se añade `qore_native_g1_pre_native_side_join_v1.py` y tests de reconstrucción con dos archivos JSONL **por lado**: BID y ASK, cada uno con `event_time_utc`, `native_sequence` y `price`. El manifest incluye SHA256 individual de ambos bytes, modo histórico, contrato único y el submanifiesto del quote gate. El algoritmo agrupa los timestamps de ambos lados y utiliza exclusivamente el **último BID y ASK con event time <= instante de decisión**, sin interpolar, inventar recibo en tiempo real ni mirar a futuro. Al faltar un lado, no publica snapshot. Si hay más de un update al mismo milisegundo, se procesan antes de emitir UNA foto de ese instante.

**Importante:** estos JSONL ya fueron decodificados; no se confunden con paquetes protobuf autenticados. El test independiente de cTrader `ProtoOAGetTickDataReq` + `hasMore`, escalado entero de precio, intervalos de 7 días, identidad de cuenta/corredor y fidelidad del decoder sigue pendiente. La reconstrucción es **interna a streams declarados**, no adquisición real, ni prueba de su cobertura completa ni aptitud económica.

**Hallazgo fuente PR #803 confirmado documentalmente:** [diagnóstico #38183622754](https://github.com/mezas3238-hue/qore-core/actions/runs/38183622754) reportó `CH_ACCESS_TOKEN_INVALID` en account-list; la app sí autenticó; **0 BID/ASK descargados**. El remedio exige nueva autorización legítima de credenciales DEMO en GitHub Secrets fuera del chat, no suposiciones ni reintentos ciegos de refresh. El bloqueo se registra como `CTRADER_DEMO_ACCOUNT_AUTH_BLOCKED` hasta nueva ejecución positiva con artefacto SHA.
