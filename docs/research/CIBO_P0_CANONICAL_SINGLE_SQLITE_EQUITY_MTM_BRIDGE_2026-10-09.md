# QORE CORE CIBO P0 — Same-SQLite PAPER portfolio equity MTM + QDLE native risk bridge

**9 octubre 2026** · Integrador **PR #745** · PAPER research, no live orders · **No 4-arm financial replay claimed**.

## Implementación confirmada

A la autoridad única `src/qore/infrastructure/qdle_paper_book.py::PaperQDLE` se conecta `src/qore/infrastructure/cibo_p0_paper_portfolio_mtm.py::CanonicalPaperPortfolioMtm`. **La contabilidad no abre un segundo SQLite**: usa `qdle._tx()` y tablas `paper_cash_account`, `paper_mtm_positions`, `paper_mtm_event_log`, `paper_mtm_snapshots` dentro del **mismo archivo** de reservas QDLE.

Controles:
1. Saldo inicial PAPER $60, no negociable después de reinicio. Los OPEN debitan comisión una sola vez y deben corresponder a `PAPER_FILLED`, precio, volumen y símbolo físico. **La comisión total del OPEN debe coincidir exactamente con `fee_usd_per_lot × lots` de la especificación QDLE del mismo símbolo.**
2. Un CLOSE incorpora resultado bruto y comisión de cierre exclusivamente si el libro canónico ya contiene `PAPER_SETTLED` con **igual request_id / timestamp / realized_gross_usd**. Repeticiones idénticas son idempotentes; eventos contradictorios fallan.
3. Cada `mark(at,...)` calcula NAV `cash + sum(unrealized executable bid/ask)` con las posiciones **simultáneamente abiertas**. Largo se valora con BID, corto con ASK. **Si falta un precio causal de cualquier posición, no se registra un mark parcial ni se inventa PnL=0**. UTC obligatorio y rechazo de cotizaciones futuras o atrasadas.
4. El cash DD y el equity MTM DD se conservan separados, acumulando máximos observados. Sin marcas densas para cada activo y cada momento de riesgo, el DD sobre ticks completo **NO se considera certificado**.
5. **Se fortaleció `QDLE.reserve_for_trader` cuando encuentra el esquema MTM adjunto**: antes de reservar, dentro de su transacción atómica, verifica igualdad entre `PAPER_FILLED` de QDLE y posiciones MTM activas; que el último evento económico sea `MARK` completo; que el `at` del mark sea la época exacta del snapshot de capital; y que `equity` del mark sea exactamente el NAV `qore_trading_capital_usd` publicado. Si cualquier condición falla, **`QDLEError` y 0 nuevas reservas**, sin borrar ni «estimar» riesgo.
6. Los libros PAPER antiguos que aún no anexan el esquema MTM conservan su suite de regresiones: esta restricción solo se habilita cuando existe `paper_cash_account` en **el mismo** SQLite de QDLE.
7. Máximo riesgo abierto 5% del NAV reconciliado después de las comisiones, conserva bloqueos exclusivamente físicos/económicos; no se restaura `THREE_SETTLED_LOSSES_HAIR_CUT`.

## Protocolo operativo correcto para el runner cuatro escenarios

Cada escenario **A-X, A-Y, B-X y B-Y es un universo alternativo**: necesita su propio SQLite `PaperQDLE` con un único libro por escenario, una sola cuenta económica por escenario y **nunca** compartir saldo/reservas entre brazos.

Por cada época cronológica:
- Primero aplicar los cierres PAPER auténticamente modelados y confirmar `PaperQDLE.paper_settle` + `CanonicalPaperPortfolioMtm.book_close` (misma identidad/gross).
- Obtener precios ejecutables BID/ASK previos o contemporáneos del timestamp para **todas** las posiciones todavía abiertas.
- Persistir `CanonicalPaperPortfolioMtm.mark`. Si hay huecos de cotización, abortar la aprobación de entradas y retener `INCOMPLETE_PRICE_PATH`.
- Publicar `QDLEAccount` con `qore_trading_capital_usd=mark.equity_usd`, `qore_unreserved_risk_usd=same equity`, `sovereign_free_source_usd=same equity` y márgenes del broker **antes** de reservas PAPER. QDLE descuenta reservas `HELD/PAPER_FILLED` exactamente una vez.
- Obtener cuatro votos económicos **FRESCOS** de ese mismo NAV, epoch y cartera; construir propuesta con ATR14 de temporalidad nativa y precio side-correct disponible en/antes de decisión.
- Autorizar reserva y confirmar el `PAPER_FILL` solo con un evento de ejecución causal; llamar `book_open` para debitar comisión inmediatamente.
- Tomar marcas continuas durante la vida del portafolio, inclusive variaciones intrabar si los ticks originales permiten demostrar el máximo DD. **Nunca estimar equity= cash** mientras haya posiciones abiertas.

No se ha conectado todavía el runner A/B×X/Y de 3.368 a este motor. Tampoco existen aportaciones históricas verificadas de tick bidask M1 VT31, USDJPY contemporáneo ni tarifas antiguas en la ejecución CI del corpus. Ningún PF/DD nuevo es certificable.

## Evidence

- [GitHub Actions **#38010799231 SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/38010799231), SHA **`fd3ca54b80e1a29c09e53525462dc3b767dc4a68`**: 9 pruebas equity MTM + 11 PAPER canónico + 17 QDLE regression = **37/37**. Incluye prueba de divergencia entre NAV publicado y MTM, atraso/falta de quote, contabilidad doble de comisiones, capital al reiniciar, doble fill y asentamiento parcial de ledger.
- [CI seal original 3.368 **#37997029969 SUCCESS**](https://github.com/mezas3238-hue/qore-core/actions/runs/37997029969) verifica siete Traders H1=2229/H4=493/M1=484/M15=162, pero el run **no recibió un paquete de historia broker verificable** y clasifica los 3368 como evidencia pendiente.
- Auditoría global **Legacy Stack Quarantine** ha hallado **20 import edges** prohibidos, varios desde módulos Native MAX cognitivos; esto no se resuelve eliminando la cognitiva ni simulando «PASS». Debe reconectarse al stack canónico o verificarse linaje de dependencias con CI real. **Zero Open Work Gate** continúa bloqueante para certificación global.

## Remaining requirements

1. Reconstruir/cargar fuentes históricas 2019–22 de bid/ask causal en M1 para 484 VT31 y de todas las estrategias, serie USDJPY, OHLC TF nativa y comisión por cuenta; asociar SHA con broker/pipeline verificado.
2. Integrar `CanonicalPaperPortfolioMtm` en **un runner por brazo** con programador global por timestamp para que fuentes actualicen toda la cartera antes de cada decisión. Hoy está implementado y probado como servicio, **no** como four-arm replay ejecutado.
3. Integrar salidas ATR14 (50% parcial en min grid, BE, trailing, defensiva) y resolver intrabar/sesiones, track cash+equity DD/fee completa y auditorías anual/Trader.
4. Cerrar reconciliación Git entre PR #745 y #746/#749. El adapter canónico pasó 39 pruebas en #749 pero queda DRAFT.
5. No afirmar FF 0.716/0.621 antiguos como nueva medición después de los cambios, no activar broker LIVE ni VPS.

**STATE: SAME_SQLITE_MTM_ENGINE_CI_PASS / NAV_FINANCING_BOUND / 37_TESTS_PASS / FOUR_ARM_RUNNER_NOT_YET_INTEGRATED / HISTORIC_BROKER_DATA_ABSENT / NO_LIVE**
