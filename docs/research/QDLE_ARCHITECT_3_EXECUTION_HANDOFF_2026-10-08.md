# QDLE — Arquitecto 3/3, reporte de implementación y continuidad P0

**Fecha:** 2026-10-08  
**Repositorio:** `mezas3238-hue/qore-core`  
**Rama aislada:** `agent/cibo-architect-3-qdle-mt5-physical-20261008`  
**Issue:** [#739](https://github.com/mezas3238-hue/qore-core/issues/739)  
**PR de este arquitecto:** [#741](https://github.com/mezas3238-hue/qore-core/pull/741) (**DRAFT, NO LIVE**)  
**PR integrador original QDLE:** [#735](https://github.com/mezas3238-hue/qore-core/pull/735) (**DRAFT, NO LIVE**)  
**Handoff común de tres arquitectos:** `docs/research/QORE_CIBO_THREE_ARCHITECT_MASTER_HANDOFF_2026-10-08.md`  
**HEAD base recibido:** `df10bf9d3def78a69c02dfc1292de49a0027529f`.

## 1. Cambios comprobables hechos por Arquitecto 3

1. El workflow `.github/workflows/qdle-p0-atomic-engine.yml` ahora escucha `push` en la rama 3 e incluye las suites `test_qdle_partial_fills.py` y `test_qdle_mt5_fee_publisher.py` además de la batería QDLE precedente.
2. Se añadieron **14 tests sintéticos de fills parciales y conciliación**: fills completados por dos deals; remanente cancelado por evento broker; overfill; deal ID globalmente único; idempotencia de replays; ticket de posición no compartible entre señales; remanente cancelado impide nuevos deals; bloqueo de multi-ticket/netting/hedging no soportados; no liberación sin cobertura QORE; comprobación de volumen broker, crash/restart, settlement de cierre única vez y estado desconocido retenido.
3. Se reparó una avería de producción en `scripts/qdle_mt5_metadata_publisher.py`: instanciaba `VerifiedFee(usd_per_lot, evidence)` sin el indicador exigido `covers_open_and_close=True`, de modo que la publicación de cualquier tarifa siempre fallaba. La nueva función `verified_roundtrip_fee_for_symbol` exige que el objeto JSON de comisión incluya **un booleano real `covers_open_and_close: true`**, importe USD por lote finito y no negativo, e identificador de evidencia no vacío. Tarifa FX apertura solamente, comisión NDX100 desconocida o base XAUUSD no verificada **no cumplen** el contrato y no deben marcarse verificadas. El booleano no convierte una pantalla o declaración del operador en prueba autenticada.
4. Se corrigió `src/qore/infrastructure/qdle_mt5_read_only.py`: `VerifiedFee` comprobaba `NaN < 0` antes de verificar finitud, provocando una excepción decimal no controlada. Ahora un valor no finito es rechazado como `QDLEError` fail-closed.
5. Se añadieron **6 tests de contrato de tarifas** (campo faltante, bool falso/string/entero, índices desconocidos, importes negativos/NaN, fuente vacía, flujo hasta símbolo MT5 y tasa cero solo con evidencia explícita).
6. No se editaron los módulos de Arquitecto 1 (#737) ni Arquitecto 2 (#738).

### Evidencia CI exact-SHA

- [Run 37851542935](https://github.com/mezas3238-hue/qore-core/actions/runs/37851542935): SUCCESS, commit `0dedd1f6a772c6332441e66679dcc444a3cc379c` (14 tests nuevos parciales; el conjunto QDLE anterior pasó).
- [Run 37851774703](https://github.com/mezas3238-hue/qore-core/actions/runs/37851774703): FAIL, se descubrió `Decimal('nan')` no atrapado por `VerifiedFee`; fallo reparado en código, **no ocultado**.
- [Run 37851841818](https://github.com/mezas3238-hue/qore-core/actions/runs/37851841818): **SUCCESS** exact-SHA `98ffeea3a218e231dabe09b6525c43091643b999`; 89 unittest de los 13 módulos invocados y 3 gateway pytest passed (12 deselected), incluyendo los **14+6** nuevos. Esta es evidencia técnica sintética, NO prueba broker-real ni aprobación de estrategia.

## 2. Investigación solo lectura sobre VPS

Repositorio puente GitHub de operaciones: `mezas3238-hue/qore-vps-control`. La política expuesta `CONTROL_POLICY.json` prohíbe live/real capital y arbitrary shell; respeta solo operaciones tipadas.

- Resultado previo `results/20261008T180400Z-qdle-mt5-readonly-processes-001.json`: operación `list_processes` dio `ok:true` y señaló un proceso `terminal64`; eso NO demuestra cuenta conectada/servidor ni respuesta de `order_calc_profit`.
- Resultado previo `results/20261008T180400Z-qdle-mt5-readonly-qore-directory-001.json`: `C:\\QORE` existe y contiene directorios `scripts`, `src`, `tests`; no demuestra que el checkout incluya QDLE HEAD.
- Último heartbeat leído durante esta intervención: `2026-10-08T21:59:03.2517003Z`, puente `0.4.2`. **No asegurar que el puente siga online**.
- Se publicaron **dos solicitudes de solo lectura** en el puente, `commands/20261008T220845Z-architect3-qdle-git-head-readonly-001.json` (`git_head` para `C:\\QORE`) y `commands/20261008T220845Z-architect3-qdle-scripts-readonly-001.json` (`list_directory` de `C:\\QORE\\scripts`). Al redactar este reporte, sus `results/` **no estaban presentes**: NO atribuir lectura ni cifras actualizadas hasta ver el resultado.
- **NO se ejecutó** un probe broker nativo desde este arquitecto. `qore-vps-control` no tiene operación tipada `order_calc_profit/order_calc_margin/order_check`; no intentar evadir la política con comandos arbitrarios, `pytest_target` u órdenes.

## 3. Invariantes congelados para Arquitectos 1/2/3

- Broker FundedNext **USD 2000 para margen**, capital propio QORE **USD 60 inicial**. Presupuesto bruto inicial de pérdida económica por entrada **5% x NAV QORE = USD 3**. Esta fracción permanece en 5%, dólares cambian con NAV realmente conciliado.
- QDLE interseca los límites de Sizing, CIBO Compuesto, Adaptive Leverage y Portafolio Compuesto. No sumar 4 veces 5%, no usar equity MT5 como referencia 5%, no forzar volumen mínimo no financiable ni confundir señal con fill.
- `order_calc_profit`, `order_calc_margin`, `order_check`, grid volumen, free margin, fee completa, margen abierto y provider rules deben estar causalmente frescos y autenticados antes de LIVE.
- Fills parciales actuales están soportados en **un solo ticket de posición**. Multi-ticket, netting agregativo o hedging que comparten posición quedan **fail-closed**, no reconciliados. Estado `SENDING` desconocido conserva fondos; no liberar por timeout.
- El replay económico de 3.368 señales (2019-2022) y fichas broker de fotos 2026 sigue `FINANCIAL_CERTIFICATION=REJECTED` por causalidad/fees/MTM. No promover PnL, DD, lotes o viabilidad como resultados LIVE.

## 4. Bloqueos P0 que deben seguir visibles

1. Recuperar resultados actuales del puente y verificar `git_head`, rama y disponibilidad del terminal, sin mezclarlo con un examen broker autenticado.
2. Crear una vía **READ-ONLY explícitamente permitida, autenticada y no mutante** para consultor `account_info`, `positions_get`, `orders_get`, `symbol_info`, `symbol_info_tick`, `order_calc_profit`, `order_calc_margin`, `order_check` sobre seis símbolos, sin credenciales de cuenta/secretos en GitHub.
3. Verificar tarifa efectivamente cobrada **open+close** para Forex, fórmula y base de `XAUUSD 0.0016%`, tarifa NDX100 (actualmente desconocida), swaps, sesiones y spread/slippage. Valorar coste dependiente de nocional, precio y duración con quotes contemporáneas; no rellenar cero ni extrapolar tasas sin prueba.
4. Diseñar broker deal reconciliation que vincule **order_id, deal_id, position_id, volumen neto, cancelación y cierre parcial**, también netting/hedging y múltiples tickets con pruebas con snapshots reales. El estado actual **rechaza seguro** los casos no soportados, pero eso no los implementa.
5. Construir replay con datos actuales auténticos (sin fecha as_of falsificada), PnL causal, MTM intratrade, stop-out irreversible, provider trailing MLL, costos completos, ablations auténticas de los cuatro motores y atribución separada de señal → propuesta → orden → fill → cierre.
6. Revisar defectos **globales**, `Zero Open Work Gate` y `Legacy Stack Quarantine`, por sus arquitectos dueños; no modificarlos ni silenciarlos desde este PR.
7. Mantener PR #735 y #741 **DRAFT / NO LIVE**. Nunca conectar `order_send` antes de cerrar estos gates y autorización explícita.

## 5. Contrato de entrada al publicador de tarifas

La clave por símbolo en `--verified-fees` debe ser:

```json
{
  "EURUSD": {
    "usd_per_lot": "IMPORTE_TOTAL_USD_POR_LOTE_DOCUMENTADO",
    "evidence": "IDENTIFICADOR_DE_DOCUMENTO_O_RECIBO_BROKER",
    "covers_open_and_close": true
  }
}
```

**No es un valor ejemplar de comisión:** `IMPORTE_TOTAL...` debe sustituirse por el dato broker auténtico antes de ejecutar; la sola presencia del campo `true` no acredita la procedencia. El lector QDLE rechaza la omisión de esa bandera y valores no numéricos/incompletos. Dejar instrumentos sin tarifa confirmada en modo no-live.

**Conclusión:** se cerró una brecha concreta de cobertura de parciales y se repararon dos defectos verificables del contrato de tarifas. El alcance unitario es GREEN exact-SHA; certificación financiera y física broker-real permanecen NO.
