# P0 — VT31 M1→M5, entrada causal y reconciliación 540/246 · 2026-10-09

**Repo:** mezas3238-hue/qore-core · **PR ejecución científica:** #748 · **autoridad PAPER:** coordinar #746/#745 · **Entorno:** GitHub Actions/Trader Lab PAPER; **NO LIVE**, NO VPS, NO MT5 order_send.

## Veredicto de código, no hipótesis

Se verificó `scripts/cibo_trader_lab_native_qdle_market_atlas_3368.py` del replay [#37957631672](https://github.com/mezas3238-hue/qore-core/actions/runs/37957631672), SHA `fb400ac27c4139c3446de33c8fa25e4d747ee970`. El runner:
1. Reconstruye `at = original.market_decision_at` de las **3.368** señales únicas originales; no prefiltra VT31.
2. Busca `pos = bisect_left(opened, at)` en velas Market Atlas **M5**, rechaza hueco mayor a 5 minutos y usa `first = bars[pos]`.
3. Determina `midpoint = first.open` y `entry = midpoint ± screenshot_spread/2`; ese mismo precio y distancia al SL entran en la propuesta económica QDLE **con as_of=at**. Cuando `first.opened_at > at`, el precio de una apertura **futura** queda indebidamente presentado como cotización conocida al decidir; **look-ahead de valoración** y retraso temporal de fill son defectos diferentes.
4. PAPER abre en `first.opened_at`, no necesariamente en el primer instante de ejecución del patrón VT31 M1. El desfase observable para entradas admitidas debe medirse `first.opened_at - market_decision_at`, no presumirse 4 minutos para todos.
5. El mismo runner contabiliza **3.086 BANK** (67 PAPER abiertos), **233 MEDIUM** (131), **49 ATTACK** (48): **3.098 sin lote financiable**; **3.097** con `REQUESTED_USD` como límite dominante. Esto explica la caída a **246 operaciones** en términos de solicitudes/riesgo/grilla de lote; no hubo exclusión global de VT31 ni R38/GBPJPY. Ambos aparecen aún con PnL PAPER negativo en #37957631672 (NDX100 −$9,4925; GBPJPY −$8,6949).

El segundo replay [#37956379198](https://github.com/mezas3238-hue/qore-core/actions/runs/37956379198), de la **misma población de 3.368**, hizo **540** aperturas, **538** cierres; PF **0,716603**, PnL **−$51,1746**. #37957631672 hizo **246/246**; PF **0,621224**, PnL **−$41,7118**. No inferir que «294 operaciones perdedoras quedaron fuera», porque la política, los lotes financiables y el path de caja varían. Sin matriz por fingerprint y cohorte pareada, el signo de las operaciones removidas y el efecto de filtrado no están identificados.

## Contrato de evidencia, bloqueos

**Barrera 1 — una sola autoridad PAPER** (#745/#746). Unificar `PaperQDLE` y `QDLE(research_paper_mode=True)` en una fuente única de reservas atómicas/idempotentes y retiros por settlement. No declarar comparable el PF entre PRs independientes ni realizar nuevo tuning de QDLE antes de completar gate exact-SHA. Evitar reserva doble y falsificación de broker.

**Barrera 2 — auditoría temporal VT31 por oportunidad original** (#748). Extraer los 484 fingerprints `trader_id=VT31_NAS100`, confirmar `decision_context.ctx_timeframe=M1` (no inferir de M5). Por cada uno enlazar `market_decision_at`, `signal_at`, `qdle_at`, `paper_entry_at` cuando existe, `intended_entry`, `paper_entry_price`, SL/TP, lot, límite QDLE, resultado PAPER. Para cada run producir `n_opened`, `n_settled`, `n_unfundable`, `n_unassessable`, histogramas de delta en segundos/minutos y casos `next_M5_open > decision_at`. Sin PAPER fill no imputar delay real; alternativa solo estimación matemática `ceil_5m(decision)` marcada `CALENDAR_BOUND_NOT_ATLAS`.

**Barrera 3 — cotejo 540/246 por fingerprint, con exactamente los mismos 3.368 IDs.** Tabla cruzada `OPEN_BOTH`, `ONLY_540`, `ONLY_246`, `NEITHER`, además de motivo de rechazo, modo BANK/MEDIUM/ATTACK, `REQUESTED_USD`, risk_usd, cash_usd y saldo del instante; reconciliar además todas las fuentes Trader separadas. Los 294 son **diferencia de totales**, no necesariamente número de señales `ONLY_540`: puede haber sustituciones `ONLY_246`. No afirmar filtrado beneficioso sin cohortes pareadas con mismo precio/riesgo/costo y un libro unificado.

**Barrera 4 — reparar causalidad antes de comparar edge.** Valuación y voto QDLE a T solo con últimas cotizaciones observadas `quote_timestamp <= T` (barra M5 **cerrada** antes de T o tick M1 verificable). Si hay fill PAPER posterior `next_open >= T`, revalidar `all_in_risk`, margen y comisión con precio de fill, ajustar lote a grilla o `NO_FILL`; nunca valorar al pasado con `future_M5_open`. No se autoriza inventar ticks M1 a partir de M5. Para VT31, reconstruir setup nativo `src/qore/infrastructure/traders/vt31_silver_bullet_r2_2.py` y M1 de la misma era/mercado. Si falta M1 verificable, emitir `M1_NATIVE_ENTRY_UNVERIFIABLE`, no llamar resultado desfasado «win rate real de VT31».

**Barrera 5 — experimento falsable de efecto del timing.** En señales M1 con origen y ruta demostrados, comparar (A) el precio histórico genuino ejecutable al **primer instante elegible M1** después de confirmación, (B) siguiente M5 abierto, (C) siguiente tick elegible y (D) control temporal +1/+3/+4 minutos (si datos permiten). En cada brazo reevaluar QDLE y fee/grid, congelar código, decisiones y presupuesto, respetar tiempo causal y reportar `entries_changed`, `fill_price_delta`, stop/TP, MFE/MAE, PF, expectancy, DD MTM y errores de cobertura; **sin datos reales M1/bid-ask no se puede concluir** que el 16,85% fuera causado por retraso. Separar diagnóstico en muestra quemada de prueba OOS nueva.

## Qué sí y qué no explica el PF
- PF 0,621 vs 0,716 representa peor razón ganancias brutas/pérdidas brutas de **muestras distintas**.
- Capital residual 18,29 vs 8,69 indica menor pérdida neta PAPER, **no** superioridad de las entradas admitidas a igual lotaje.
- VT31 #37956379198 aportó 89 cierres, PF 0,450 y 16,85% win rate; ese resultado es **solo escenario M5/fixed-spread** hasta reconstruir causalmente su señal M1.
- PnL NDX100 negativo también en 246 muestra que **VT31 no fue eliminado**. Falta prueba exacta de cuántas aperturas tuvo VT31 en 246; exigir matriz generada, no inferir del PnL agregado.

## Entregables/gates
1. `scripts/cibo_p0_vt31_m1_m5_join_540_246.py` que lee los **dos JSON sealed** y el manifest original, valida conjuntos/sha y emite `cibo-p0-vt31-m1-m5-selection-comparison.json`.
2. Tests sintéticos: exact-3368, 7 Traders, 484 VT31, identificación de `PAPER_OPEN`, rechazos, retiro y reingreso, temporización aware, `future_M5_open`, No-fill sin imputación de desplazamiento, control de duplicados y mismatch de fuente.
3. **La auditoría de tiempos con dos replays** solo se considera empíricamente confirmada cuando GitHub Actions suba el artefacto de comparación y se verifique su SHA. Nunca cambiar la política LIVE con este estudio retrospectivo.
4. Una sola autoridad PAPER + fuente M1 verificable + no look-ahead + sensibilidad de coste + nuevo OOS son puertas separadas: no presentarlas como completadas juntas.

**Status:** `RESEARCH_SOURCE_TIMING_DEFECT_CODE_CONFIRMED / DELAY_DISTRIBUTION_NOT_YET_MEASURED / CAUSAL_WINRATE_EFFECT_UNPROVEN / BOOKS_NOT_UNIFIED / NO_LIVE`.
