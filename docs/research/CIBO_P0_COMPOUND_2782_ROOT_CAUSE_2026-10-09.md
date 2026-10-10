# P0 — Auditoría causal de los 2.782 bloqueos de CIBO Compuesto en 3.368 entradas

**Estado:** AUDITORÍA COMPLETADA / ROOT CAUSE DE PRIMERA RESTRICCIÓN CONFIRMADO / **SIN CAMBIOS DE POLÍTICA**.  
**GitHub Actions verificado:** [run #37909235818 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37909235818), [archivo de 3.368 razones por señal #11605372636](https://github.com/mezas3238-hue/qore-core/actions/runs/37909235818/artifacts/11605372636).  
**Entrada sellada:** [replay CEO manager + QDLE #37907644177](https://github.com/mezas3238-hue/qore-core/actions/runs/37907644177), artifact `11605550958`, ZIP SHA256 `cb52e91e5aff43a251cff431b6bfddbdb7197f60281684d6dc346d3255df69b2`, `qdle-cibo-manager-economic-sl.json` (3.368 recibos).
**Script read-only:** `scripts/cibo_p0_compound_replay_audit.py`, test `tests/infrastructure/test_cibo_p0_compound_replay_audit.py`, workflow `.github/workflows/cibo-p0-compound-3368-root-cause-audit.yml`. Branch `agent/cibo-sovereign-integration-p0-20261008`, PR #745.

## Conclusión ejecutiva

**Los 2.782/2.782 rechazos físicos por binding `CIBO_COMPOUND` surgen de UNA SOLA regla específica**: `THREE_SETTLED_LOSSES_HAIR_CUT`, que reduce el techo de riesgo por entrada desde 5% del QORE NAV reconciliado en el control a **2,5%** tras tres pérdidas consecutivas realmente registradas en el cashbook *simulado*. En esas 2.782 operaciones:

- `CIBO_COMPOUND.cap ≈ 0.025 × control_NAV` con tolerancia inferior a `1e-9 USD`, 2.782/2.782.
- Coste del lote mínimo `0.01 × (stop_loss_USD_per_whole_lot + roundtrip_fee_USD_per_whole_lot)` estaba **por encima del cap 2,5% pero dentro del 5%** en 2.782/2.782. Por tanto, no se trató de costes «imposibles para 5%»: el recorte defensivo hizo inasequible el mínimo.
- En los registros, Sizing, Portafolio Disponible, cap lotes de Leverage y margen provisional FundedNext no presentaron una restricción adicional del mínimo **al mismo snapshot** para ninguno de esos 2.782. Esto es una **sensibilidad estática por operación**, no 2.782 fills nuevos probados; liquidar las operaciones adicionales cambiaría NAV, racha de pérdidas, concurrencia, fuente y DD.
- **NUNCA modificar `Cibo Compound` para elevar apertura solo por esta tasa**. Puede ser un guard deliberado válido frente a drawdowns. QDLE funciona al respetarlo.

### Fórmula de política fuente, no hipótesis de reserva del 70%

Source: `src/qore/infrastructure/cibo_compound_capital.py::propose_p0_compound_vote`:

```python
base = observation.base_entry_budget_usd  # 0.05 * NAV
available = observation.risk_cash_remaining_usd
chronological = sorted(observation.reconciled_cashflows, ...)
streak = number_of_consecutive_recent_negative_net_settlements
factor = Decimal("0.5") if streak >= 3 else Decimal("1")
approved_risk_usd = min(available, base * factor)
```

Causal `NAV = 60 USD + sum(reconciled_cashflows.net_usd)`; cash still available: `max(0, NAV - protected_capital - floating_loss_reserve - risk_reservations)`. **En este replay** `protected_capital=0`, `floating_loss_reserve=0`, y `risk_reservations` representan operaciones abiertas del escenario de control; no existe reserva protegida del 70% en la función. El programa de replay reconstruye `reconciled_cashflows` sintéticos con `recent_settlements[-3:]` y un cashbook agregado previo. Esa evidencia no proviene de settlements reales de MT5 ni de cierres CIBO.

El estado monetario viene de **NAV simulado por 359 operaciones con SL/salidas originales del Trader** que cerraron el capital USD60→USD9,517. **NO** se conoce cuál sería el NAV del CIBO administrador de 568 propuestas porque falta path bid/ask y resultados de los 209 stops alternativos. No transferir la secuencia de derrotas del control al manager verdadero como si fuese prueba de solvencia futura.

### Censo por instrumento

| Instrumento | Oportunidades recibidas | Limitadas principalmente por racha de 3 pérdidas |
| --- | ---: | ---: |
| AUDJPY | 673 | 571 |
| EURUSD | 495 | 387 |
| GBPJPY | 618 | 513 |
| GBPUSD | 606 | 503 |
| NDX100 | 484 | 389 |
| XAUUSD | 492 | 419 |
| **Total** | **3368** | **2782** |

Descomposición: de las 2782, **2337** tenían propuesta de SL económico y **445** mantenían SL estructural. En ambos grupos la primera restricción era el presupuesto 2,5% causado por la regla de racha.

Distribución cronológica por año de esas restricciones (en el escenario de control): **2019: 203; 2020: 1.035; 2021: 1.090; 2022: 454**. Primer bloqueo registrado 26 jul 2019; último 29 jun 2022. La prolongación es consistente con un **riesgo de enclavamiento económico**: la protección por tres pérdidas baja el lote máximo bajo el mínimo broker; sin operaciones nuevas, no llega una liquidación positiva que pueda restaurar la racha. No implica que todos los períodos estuvieran en enclavamiento ininterrumpido: hubo aperturas aún financiadas.

### Matriz de hipótesis originales

| Hipótesis | Evidencia del P0 | Resultado |
| --- | --- | --- |
| Reserva protegida demasiado alta | `protected_capital_usd=0`, `floating_loss_reserve_usd=0` en este programa; fórmula de compound no hardcodea 70% | **No explica los 2782 en este replay**; no extrapolar a LIVE |
| NAV equivocado/no conciliado | `initial NAV=60+cashbook sintético control`, sin broker USD2000 como capital propio | **NAV alimentado por control no administrado**, problema de validez científica del replay (no se ha identificado un bug de Decimal ni inversión de USD) |
| Reinvierte muy poco beneficio | Función `propose_p0_compound_vote` usa **base del 5% de NAV** y recorte por racha; no exige beneficio compuesto realizado positivo para la entrada en esta función | **No es la restricción principal de esos 2782** |
| Regla mal aplicada/tope por entrada | Cap se aplica **por oportunidad**; 3 pérdidas producen factor 0,5 y mínimo 0,01 ya no cabe | **Causa matemática confirmada.** Si es demasiado restrictivo es decisión de política/arquitectura, no bug aritmético demostrado |

### Sensibilidad sin cambiar motor: si solo se retirara la mitad defensiva

Bajo los **mismos snapshots del control**, **2782/2782** lotes mínimos `0.01` superan el 2,5% pero no el 5% de NAV. Los otros límites **registrados** (Sizing, Portfolio Source, Leverage lot cap y Margin 2026 proxy) resultan suficientes a ese instante. Por ello, `isolated_removal_half_risk_cap_minlot_price_feasibility=2782` — esta es **asequibilidad matemática de un solo intento con el snapshot original**, **NO** una simulación QDLE tras abrir las 2782, ni capital final, DD, PF o autorización para quitar la regla. Una cartera con nuevos fills alteraría todas las decisiones siguientes.

**Criterios de éxito congelados antes de una ablation de política de rachas:**
1. Identidad 3368/3368, factor y motivos por señal, budget NAV 5% íntegro, QDLE real grid y ALL-IN stop+comisiones+slippage; Bank/Cushion segregados.
2. Probar *sin tocar producción* al menos tres tratamientos shadow sobre idénticos inputs: política actual `3-lossses→50%`, alternativa `cooldown temporal con recuperación controlada`, alternativa `posición pequeña y stop viable, sin exceder presupuesto`; no usar `ALLOW_ALL`.
3. Reconstruir SL/TP y parciales/trailing/BE/defensa sobre rutas ejecutables, incluir gaps y evidencia ATR; recomputar NAV 5% **de cada brazo** y la racha de ganancias/pérdidas real de cada uno, no copiar desde control.
4. Beneficio neto OOS no consumido y PF >1,20 como criterio mínimo candidato, DD MTM objetivo <=20%, tolerable <=25% y **ningún breach** a fuente/proveedor. No aprobar solo por mayor número de lotes.
5. Exigir validación MT5 read-only de `symbol_info`, `order_calc_profit`, `order_calc_margin`, spreads, stops, lotstep, fee OPEN/CLOSE y disponibilidad; no SEND en investigación.
6. Si faltan barras/ticks o verdadera atribución de capital CIBO Compuesto, reportar `INCONCLUSIVE`, no inventar retorno.

## Continuidad siguiente arquitecto

**No modificar ni el 50% ni el número de pérdidas todavía.** Instrumentar la procedencia de `reconciled_cashflows`, `loss_streak` y duración de la reducción en el runtime verdadero; diferenciar defensa de exposición vs impedimento indefinido de recuperación. Conseguir datos de mercado causales y exits gestionados por CIBO, recomputar libro Bank/Cushion y QDLE. Comparar experimentos de protección por racha sobre una cartera realista y sin leakage; solo luego proponer una transición de política versionada por experimento con criterios preregistrados.
