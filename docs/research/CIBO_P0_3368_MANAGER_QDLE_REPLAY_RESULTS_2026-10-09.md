# CIBO P0 — Replay pareado de 3.368 oportunidades: administrador + 4 motores + QDLE

**Fecha:** 2026-10-09 · **Run verificado:** [GitHub Actions #37904592323](https://github.com/mezas3238-hue/qore-core/actions/runs/37904592323) **SUCCESS** · **Artefacto JSON (3 informes + 3.368 receipts)**: [#11603757283](https://github.com/mezas3238-hue/qore-core/actions/runs/37904592323/artifacts/11603757283) · **Branch:** `agent/cibo-sovereign-integration-p0-20261008`.

## 1. Qué se ejecutó realmente

El workflow `.github/workflows/cibo-p0-manager-qdle-replay.yml` cargó el manifest sellado de 3.368 oportunidades 2019–2022 (source SHA256 verificado). Ejecución:
1. `scripts/cibo_p0_3368_manager_intake_sensitivity.py`: CIBO **RECIBE** 3.368/3.368, sin `COGNITIVE_BLOCK` ni `CAPITAL_BLOCK` de Native MAX; modela costo mínimo inicial por señal (NAV USD60, 5%=USD3) para identificar SL estructural vs candidato económico; guarda un expediente por ID.
2. `scripts/qdle_3368_dual_ledger_replay.py` en **`independent_four_motors` + `broker_grid` + `provider-trailing-usd disabled` + `swap off`**, sin `experimental-native-ceiling-report`: procesa las **3.368** señales con **el SL original** por cuatro motores Sizing, CIBO Compuesto, Adaptive Leverage y Portafolio Compuesto y QDLE con riesgo `0.05 × QORE_NAV` **dinámico tras cada liquidación**, costos OPEN y CLOSE proxy, broker nominal USD2000 solo para margen; resultados financieros estimados por el **R estructural histórico** del Trader en su fecha de salida original. Esto es un **benchmark de control sin filtro pretrade**, **no** el algoritmo completo de exits económico CIBO.
3. `scripts/cibo_p0_manager_qdle_replay_audit.py`: empareja por ID los 3.368 recibos CIBO y 3.368 receipts QDLE. **No reetiqueta resultados de SL originales como resultados de 300 stops económicos**. Los tres JSON quedaron en el artifact.

**CI:** 11 tests de administración + 17 tests QDLE en PASS, manifest digest OK, auditoría `CIBO_P0_MANAGER_QDLE_3368_INTEGRITY_PASS`, 0 MT5 SEND/fill. Duración run ~34s; la ausencia de recomputación cognitiva es intencional bajo paradigma MANAGER.

## 2. Resultados financieros **SOLO DEL BRAZO CONTROL CON SL ORIGINAL**

| Métrica | Resultado |
| --- | ---: |
| Trader opportunities received | **3368/3368** |
| QDLE four-motor evaluated | **3368/3368** |
| Candidatas con SL estructural inicial asequible (USD60, costo proxy min 0.01) | 3068 |
| Candidatas a SL económico alternativo, **no aplicado al PnL** | 300 |
| Propuestas de lotaje financiables con SL original | **359** |
| Original SL no financiable / no válido | **3009** |
| Balance QORE inicial (capital propio simulado) | **USD60.00** |
| Balance QORE final (escenario original stop) | **USD9.5174675045** |
| PnL neto simulado | **−USD50.4825324955** |
| DD máximo sobre NAV **cerrado** | **87.40357309%** |
| PF neto proxy | **0.7814715961** |
| Comisiones OPEN proxy | **USD54.07647168** |
| Comisiones CLOSE proxy | **USD54.07647168** |
| Comisiones totales proxy | **USD108.15294336** |
| Pérdidas netas brutas de operaciones perdedoras / sumatoria | USD231.01130830 |
| Ganancias netas de operaciones ganadoras / sumatoria | USD180.52877580 |
| Swaps | No modelados |
| DD intratrade (MTM) | **No medido** |
| Exits auténticas gestionadas por CIBO | **0** |
| Fills broker MT5 verificados | **0** |

**No confundir** esta referencia con 9 operaciones obtenidas bajo el OLD SELECTOR; esas 9 recibieron gates Native MAX que **no se ejecutaron** ahora. **Tampoco** afirmar que 359 fueron enviadas a mercado: son exclusivamente reservas hipotéticas QDLE con fill modelado por el simulador usando historic `entry_at` no autenticado.

### Por instrumento — con SL original y exit histórico del Trader (no CIBO)

| Instrumento | Señales recibidas | QDLE fundable | Ganadoras | Perdedoras | PnL neto proxy USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| AUDJPY | 673 | 70 | 30 | 40 | **−11.5005** |
| EURUSD | 495 | 90 | 28 | 62 | **−39.4430** |
| GBPJPY | 618 | 58 | 29 | 29 | **+9.5199** |
| GBPUSD | 606 | 61 | 25 | 36 | **−16.9610** |
| NDX100 (señal NAS100) | 484 | 56 | 12 | 44 | **+9.7350** |
| XAUUSD | 492 | 24 | 9 | 15 | **−1.8329** |
| **TOTAL** | **3368** | **359** | **133** | **226** | **−50.4825** |

**Lectura correcta**: EURUSD fue el principal contribuyente negativo; abrir más señales **sin nueva gestión de salidas** no genera automáticamente una buena curva. NDX100 tiene 44 pérdidas sobre 56 operaciones hipotéticas, aunque el saldo es positivo por magnitud de ganancias. Los datos son proxy de salidas Trader, no decisiones CIBO.

### Restricciones QDLE observadas en los 3.009 sin financiación

| First binding constraint QDLE | N |
| --- | ---: |
| `REQUESTED_USD` (presupuesto por oportunidad frente al mínimo legal) | **2554** |
| `CIBO_COMPOUND` (límite económico votado por motor) | **445** |
| `SOVEREIGN_BANK` (fuente sin cobertura) | **9** |
| `ZERO_FINANCE_CAPACITY` | **1** |
| **TOTAL** | **3009** |

**Aviso metodológico:** la primera constraint binding se deriva del motor QDLE y el orden de límites; no demuestra efecto causal marginal de relajar una sola restricción. Recalcular los límites conjuntamente y distinguir stop min fee/margin antes de formular corrección. `CIBO_COMPOUND` todavía restringe económicamente sin el selector Native; esto puede ser correcto por recursos, pero no debe camuflar una regla de no admisión.

## 3. Comparación de paradigma

| Modelo | CIBO recibe | Evaluados por QDLE | Fundables en el escenario | Capital final reportado | DD reportado |
| --- | ---: | ---: | ---: | ---: | ---: |
| OLD Native MAX selector / gate + QDLE | 3368 input | 3368 contabilidad | 9 | USD62.49 | 6.10% cerrado |
| NEW manager intake + cuatro motores y QDLE **SL original** | **3368 management receipts** | **3368** | **359** | **USD9.52** | **87.40% cerrado** |
| NEW manager **300 SL económicos alternativos** | 300 shadow candidates | sin reevaluación secuencial de SL alternativo | **NO MEDIDO** | **NO MEDIDO** | **NO MEDIDO** |

Los dos brazos con resultados históricos no miden la misma estrategia ni prueban que el filtro OLD era mejor; la diferencia procede de composición/selección de entradas, estrategia de salida modelada y capital acumulado. En particular el drawdown cerrado no prueba un DD intratrade viable ante FundedNext. **La tasa de recepción del nuevo CIBO es 100%, pero su calidad como gestor aún no está medida**.

## 4. P0 siguiente para un replay verdaderamente administrado

**Trabajo aún abierto y crítico:**
1. Integrar `TraderSignalIntake` con el stream real del Trader **antes de ejecutar**, y con el adaptador de fills **si ya fue ejecutado**; 3.368 IDs persistentes.
2. Asegurar `CiboEconomicInstruction` y cuatro motores con fuentes Bank/Cushion reales y presupuestos en NAV causal; resolver 2554 `REQUESTED_USD`, 445 `CIBO_COMPOUND` y costes por lote reales sin relajar riesgos ni fingir 0.01.
3. Para los **300 nuevos SL** usar barras/ticks cerrados predecisión + trayectorias de ejecución y `MT5 order_calc_profit` read-only o snapshot histórico; recomputar TP/hit-first/concurrencia y efecto al NAV. No usar `gross_structural_outcome_r` congelado con SL cambiado.
4. Ejecutar A1 lifecycle CIBO: parciales, trailing, BE, gestión adversa, comisiones OPEN y CLOSE, margin/swap/gap, cambios de stop y compensación/cierre bajo un escenario auditable.
5. Comparar por instrumento, tasa de gestión, QDLE lotaje, pérdidas adversas, PF neto y DD MTM; preservar riesgo máximo 5% dinámico y objetivo DD 20–25%; revalidar sobre OOS realmente no tocado antes de certificar.
6. El replay no puede acreditar fills reais del VPS: sin prueba del bróker ni posibilidad de `order_send` desde CI, se queda estrictamente en `RESEARCH`.

**Referencia de autoridad:** [CIBO paradigma ADMINISTRADOR, no filtro](CIBO_P0_PARADIGM_OVERRIDE_2026-10-09_TRADER_EXECUTION_MANAGEMENT_QDLE.md). El script Native de 11 autorizadas se mantiene como control histórico obsoleto, no como admisión de la arquitectura destino.
