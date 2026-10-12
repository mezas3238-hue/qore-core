# QORE-Alpha 2 W3 — auditoría independiente del primer GROSS (SHA original)

La primera ejecución W3 completa es [#38284821503](https://github.com/mezas3238-hue/qore-core/actions/runs/38284821503), HEAD `e7ec0e4d1cfb8b80effb9e2c1eea23524d6e716c`, 35/35 PASS, `NO_SUPPORT_PREDECLARED_GROSS`. La auditoría POSTHOC sin precios nuevos es [#38285345503](https://github.com/mezas3238-hue/qore-core/actions/runs/38285345503), 1/1 PASS, HEAD `a55da0fa6b5b11ec5c568ea22cbceabdca5c73d0`. Ambos archivos firmados SHA. Source manifest G0 SHA `1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85`.

## Falsación de la hipótesis de transición morfológica

- 33 mercados incluidos con al menos una señal cada uno, 0 mercados sin señal; 24.487 señales, 24.399 pares completos, 88 censurados sin rellenar. 10.841 pares con direcciones opuestas de CMTRL y control preevento (control no tautológico). DEV 18.266 pares, DIAG 6.133 pares; ambos pasan muestra congelada.
- Cobertura: índices 3 mercados, **2.178 señales / 2.147 pares**; metales 2, **1.623 / 1.607**; mayores FX 7, **5.137 / 5.122**; cruces FX 21, **15.549 / 15.523**. La condición no-contigua de las últimas H1 observadas, precongelada antes de outcomes W3, permite trabajar también con cierres de sesión sin inventar barras.
- Resultados gross: DEV estrategia +0,18659759 bps, delta −0,01516454 bps; DIAG estrategia +0,06924182 bps, delta +0,53515728 bps. Medios absolutos diminutos; sin spread o comisión reales no derivar rentabilidad neta.
- Bootstrap de calendario sincronizado, 4 semanas, B=4.000: DEV **IC95 delta [−0,444306; +0,425179] bps**, p centrado exploratorio 0,9435; DIAG **[−0,241776; +1,278238] bps**, p 0,1575. Ambos cruzan cero: no soporte de ventaja incremental frente al control. Hay **312/314 semanas** con pares DEV y **105/106** DIAG. La representatividad temporal es alta, pero no convierte no-soporte en edge.
- Abstenciones secuenciales registradas entre 33: `STATE_POSTERIOR_HAS_NO_EDGE_OR_POWER` 402.521; `INCOMPLETE_PAST20_OR_AMBIGUOUS_H1_GEOMETRY` 10.696; `PRE_EVENT_BASELINE_2H_UNAVAILABLE` 111; `BASELINE_ZERO_DIRECTION` 77. **No** retune Bayesian posterior 0,65/0,35, ventana 240, 20 observaciones o baseline a partir de estas cuentas.

## Estado y siguiente fase

W1 PATR, W2 PADE y W3 CMTRL constituyen **tres pruebas exploratorias** y se congelan. No hay Trader Alpha2 rentable demostrado, 0 certificados, 0 órdenes autorizadas. La historia 2016–2024 se ha consumido; nuevos ensayos requieren prereg, nueva fuente independiente y corrección de selección adaptativa. Próxima tarea obligatoria #852: fuente real BID/ASK por símbolo, spreads, comisiones, financiación, deslizamiento, PIT macro, sesiones reales y pipeline de auditoría de cada año/fold. No volver a presentar gross OHLC como net ni como backtest executable. Trabajar sólo en GitHub PR #840, sin VPS/MT5/Shared/CIBO/QDLE.
