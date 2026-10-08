# CIBO H31 — HANDOFF MAESTRO · CUATRO CALCULADORES DE LOTAJE CON CAPITAL REALMENTE DISPONIBLE

**Fecha 2026-10-08 · Estado: IMPLEMENTADO EN RAMA EXPERIMENTAL, 10/10 TESTS UNITARIOS, REPLAY 3.368/3.368 SUCCESS. NO APTO PARA PROMOCIÓN A PRODUCCIÓN.**

## Instrucción del CEO y arquitectura

El Trader origina las 3.368 señales, CIBO administra las entradas **sin rechazarlas**. Cuatro motores económicos deben calcular volumen/lotes y dinero disponible antes de ampliar las posiciones; comparten **una sola billetera**, sin contabilizar dos veces capital:
1. **SIZING**: objetivos de riesgo inicial USD2.95 al stop sobre USD60, proporción de riesgo monetario compuesto (~4.9167% de capital nominal); convierte stop USD/lot y volumen mínimo/step a lotes deseados.
2. **CIBO_COMPOUND**: verifica realmente fondos MEDIUM del banco soberano y comisiones / custodia; solo se autoriza escalado si hay fondos que exceden la reserva de seguridad.
3. **COMPOUND_PORTFOLIO**: verifica riesgo abierto global y, para ATTACK, exclusivamente capital del cushion y crédito reusable ya liquidado.
4. **ADAPTIVE_LEVERAGE**: convierte aprobaciones en lotaje legal sujeto a multiplicador nativo, proveedor y *margen monetario libre del restante equity*.

El candidato final de lote es el **menor volumen financiado** en esas cuatro etapas. Bancos, reinversión, autoridad cognitiva y administración postentrada originales no se reescriben. Los instrumentos del histórico tienen pasos: NAS100 min 0.1, paso 0.1, otros normalmente min 0.01 y paso 0.01. El proveedor vivo no ha sido consultado; **no inferir que los datos históricos son volumen/margen vigente de FundedNext**.

## Códigos publicados

- Branch: `agent/cibo-h31-lotage-bank-floor-and-free-margin-001`.
- Nuevo componente compartido `src/qore/infrastructure/trader_lab/cibo_four_motor_lotage_h30.py`.
- Integración opcional en `src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py`.
- Exposición por CLI: `scripts/cibo_trader_lab_three_mode_ceiling.py --four-motor-lotage-initial-stop-usd 2.95`.
- Suite `tests/trader_lab/test_cibo_four_motor_lotage_h30.py`.
- Workflow test `.github/workflows/cibo-h31-four-motor-margin-bank-tests.yml`, **10 tests SUCCESS**, ejecución https://github.com/mezas3238-hue/qore-core/actions/runs/37800509920.
- Workflow replay `.github/workflows/cibo-trader-lab-h31-4motor-bank-protected-295-full-replay.yml`, **SUCCESS**, ejecución https://github.com/mezas3238-hue/qore-core/actions/runs/37800515314, artefacto `11561030781`.
- Archivo completo de resultados `docs/research/CIBO_H31_FOUR_MOTOR_LOTAGE_FULL_3368_VERIFIED_RESULTS.json` commit `0cbb8b380668e1b843d82909b180f5d8cbfc3dac`.

## H30 rechazado y H31 guardada solo como laboratorio

| Métrica | Control H21 (nominal 5% pero subutilizado) | H30 sin refuerzo de reserva | H31 con reserva y margen descontado |
|---|---:|---:|---:|
| Entradas del Trader administradas por ledger | 3368/3368 | 3368/3368 | 3368/3368 |
| Capital inicial | USD60 | USD60 | USD60 |
| Capital final después 3 años | **USD3589.260487** | USD2705.993808 | USD2997.391948 |
| DD máximo | **34.35372258%** | 34.35372258% | 34.35372258% |
| Infracción piso soberano | **0** | **USD74.00000483 · RECHAZADO** | **0** |
| Objetivo stop por entrada aprobado exactamente en H31 | No aplicable: presupuesto nominal5% | 0 de 3368 | **0 de 3368** |
| Mínimo lote teóricamente sin financiación | No auditado como broker real | 27 | **1124** |
| Promover a sistema certificado | NO (DD34% >25%) | **PROHIBIDO** | **PROHIBIDO** |

*Advertencia principal*: El total 3368/3368 corresponde a **recibos de custodia de la simulación histórica**, donde CIBO conserva 1x cuando el lote no cumple. No son 3368 órdenes que realmente satisfacen liquidez de broker. H31 halló **1124 entradas** donde su margen/fondo libre no autorizaría siquiera el mínimo. El simulador preservó la posición original 1x, y por tanto la integración no puede certificar ejecución real/viable para esas filas. La ruta live deberá **fallar antes del envío de la orden** si el capital es insuficiente: el Trader no debe colocar una orden no financiable. No recortar silenciosamente las señales del banco científico.

## Resultado H31 con detalles por horizonte

| Desde 2019-07-01 | Beneficio NETO libro H31 | Saldo realizado desde USD60 |
|---|---:|---:|
| 1 mes | +USD8.500113 | USD68.500113 |
| 3 meses | +USD25.543831 | USD85.543831 |
| 6 meses | +USD28.366307 | USD88.366307 |
| 12 meses | +USD363.746163 | USD423.746163 |
| Tres años | +USD2937.391948 | USD2997.391948 |

**No** proyectar estos importes como ganancias reales de FundedNext ni de USD2.95 stop efectivamente ejecutado. Son cifras de la simulación original con 1x mandatory fallback, costes nativos y el mismo conjunto reused/burned 2019–2022.

## Bloqueo financiero demostrado en la primera señal

NAS100 primera entrada 2019-07-01 14:31 UTC, stop-risk de 1x **USD0.295** sobre **0.1 lote**. Para USD2.95 en el mismo SL, **1.0 lote = 10x**. El manifest histórico de esa señal declara `margin_per_volume=152.99` USD por lote, por lo que en esta interpretación del proveedor **USD152.99 > USD60 iniciales**. Ningún calculador legítimo puede obtener 1.0 lote con un saldo libre de solo USD60 sin otra fuente/margen/especificación autorizada. La primera H31 sigue en 1x, stop USD0.295, **NO cumple target**. `volume_step=0.1`, `minimum_volume=0.1` se obtuvieron del manifest real; no alterar stop para cambiar R. Es preciso verificar especificaciones del broker/condiciones de margen antes de determinar si otro leverage real permite la orden.

## Seguridad y ciencia

- H31 preservó 3.368 decisiones, 0 infracción soberana, pero **DD34.35%**, aún superior al **25% tolerable / 20% ideal**.
- H31 termina USD591.87 por debajo del carrier nominal H21; **no cumple STRICT PARETO**, así que **no debe mergearse ni promoverse a producción**.
- H31 instrumentó `quoted_entries=3368`, `target_attained_entries=0`, `unfunded_minimum_entries=1124`, reason counts `BANK_CUSTODY_CAP=1708`, `NATIVE_OR_PROVIDER_CAP=2072`, `MARGIN_FREE_CASH=1`.
- En H31 hay 10 pruebas unitarias con éxito. Las pruebas no sustituyen la verificación económica real ni el fresh OOS.
- Los cálculos de lotaje deben tomar `SYMBOL_VOLUME_MIN/MAX/STEP`, valor del tick, distancia stop, `order_calc_margin` o equivalente del broker, comisión ida/vuelta/spread/slippage, equity y margen libre causal y posiciones abiertas.
- Si 1.0 lote del NAS100 requiere >equity, hay **conflicto físico** entre la orden USD2.95 y cuenta USD60; alternativas legítimas: mayor saldo/margen autorizado, especificación diferente, o exposición menor que USD2.95 *declarada como incumplimiento*. **No simular fills que nunca se podrían abrir.**
- Los motor-traces se instrumentaron por etapa; la variante original permanece intacta sin activar el flag de investigación. El desfase del "ceiling" original con apalancamientos gigantes es otro régimen y nunca debe mezclarse con esta microcuenta de riesgo ~5%.

## Trabajo siguiente explícito

P0: confirmar parámetros del broker y **distinguir señales vs ejecución real** sin romper la autoridad Trader / CIBO; para certificación una señal no financiable se rechaza ANTES de enviar, aunque la investigación mantenga los 3368 inputs. Auditoría causal por trade de equity/margen y riesgo autorizado. Solo cuando se pueda financiar el objetivo, nueva simulación completa por años y rangos 1/3/6/12, pruebas científicas OOS y objetivos banco0, DD20–25%, no degradar techo. Los cuatro motores están integrados en laboratorio pero **no se ha certificado 2.95 realmente consumidos por trade**.

**Decisión de release: H31 RESEARCH PROTOTYPE ONLY, no producción.**
