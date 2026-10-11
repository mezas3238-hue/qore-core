# QORE — Londres, E2: ¿la H4 previa explica la divergencia EURUSD/GBPUSD?

**Fecha:** 2026-10-11 · **ESTADO:** `E1_BOOTSTRAP_COMPLETED / E1_STRICT_H4_UNTESTABLE / E2_OBSERVED_H4_SENSITIVITY_COMPLETED`. Investigación exploratoria **no OOS**, no trading ni mejora de reglas L1/L2.

**Evidencia:** [E1 GitHub Actions #38152004136 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38152004136), [E2 #38152552686 4/4 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38152552686); [E2 agregado #11707107547](https://github.com/mezas3238-hue/qore-core/actions/runs/38152552686/artifacts/11707107547), [EURUSD ledger #11707282202](https://github.com/mezas3238-hue/qore-core/actions/runs/38152552686/artifacts/11707282202), [GBPUSD ledger #11707416017](https://github.com/mezas3238-hue/qore-core/actions/runs/38152552686/artifacts/11707416017). [PR #780 E1](https://github.com/mezas3238-hue/qore-core/pull/780) y [PR #781 E2](https://github.com/mezas3238-hue/qore-core/pull/781). Código E2 probado `4d093b1ecd8acba4ebab73156fa583fecf7983a7`, prerregistro original E2 `d86a38ffab44c47be2eb3578512d16556ed5dec0`, **antes de leer E2 outcomes**. Fuente previa de 458 rutas inmutables en [run #38150980682](https://github.com/mezas3238-hue/qore-core/actions/runs/38150980682).

## 1. Resultados A: interacciones entre pares, con fechas comunes

La variable es **reversión del cierre a +60m ≥0,25×AsiaRange** a partir de checkpoint, y los estados `RECLAIM_INSIDE` y `ACCEPTED_OUTSIDE` son los originales, no se reetiquetaron ni ajustaron:

| Estado | EURUSD reversión | GBPUSD reversión |
|---|---:|---:|
| RECLAIM_INSIDE | 38/94=40,43% | 22/92=23,91% |
| ACCEPTED_OUTSIDE | 40/115=34,78% | 50/123=40,65% |
| Diferencia dentro de par R−A | +5,64pp | −16,74pp |

**Interacción EUR(D_R−D_A) − GBP(D_R−D_A) = +22,38pp**. Bootstrap conjunto de pares en bloques circulares **5 jornadas NY**, 2.000 repeticiones, semilla 77520261012: **IC95 [+7,34,+36,91]pp**; proporción I≤0 entre remuestreos =0,1%. Incluso teniendo dependencia por fecha de ambos pares, **la divergencia de este histórico no se elimina bajo ese procedimiento de re-muestreo**. No llamar `diferencia estructural demostrada` sin OOS, otros periodos y protocolo autoral.

## 2. Primer intento B: H4 estricto E1 BLOQUEADO (no es rechazo de hipótesis)

[Prerregistro E1](https://github.com/mezas3238-hue/qore-core/blob/research/london-eur-gbp-divergence-h4-audit-20261011/docs/research/QORE_LONDON_ISSUE775_DIVERGENCE_H4_E1_PREREG_2026-10-11.md) fijaba tres H4 consecutivas UTC con 720/720 M1 strict y close final antes de `raid_at`. **0/458** lograron 720/720: todas `H4_UNKNOWN_GAP`. E1 no pudo probar confusión H4, no permite afirmar que H4 sea irrelevante. No se imputaron cotizaciones.

## 3. Sensibilidad B E2: H4 OBSERVADA (distinta, calidad con umbrales predefinidos)

[Prerregistro E2](https://github.com/mezas3238-hue/qore-core/blob/research/london-eur-gbp-h4-observed-proxy-e2-20261011/docs/research/QORE_LONDON_ISSUE775_E2_H4_OBSERVED_PROXY_PREREG_2026-10-11.md) fue publicado tras saber que E1 estaba bloqueado, **pero antes de consultar resultados condicionados E2**. Tres H4 nominales UTC consecutivas ya terminadas antes del raid; para cada una de sus 12 horas requiere **≥45/60 M1 observadas** y último cierre de H4 como M1 observado dentro de cinco minutos de fin nominal, sin adelantar ticks ni consultar vela posterior. Se etiqueta `OBSERVED_H4_PROXY`, **NO H4 estricto ni sesgo TTrades del autor**.

| Disponibilidad H4 de checkpoints | EURUSD | GBPUSD |
|---|---:|---:|
| H4 alineado a dirección del raid | 99 | 95 |
| H4 opuesto a dirección del raid | 52 | 59 |
| H4 desconocido por cobertura M1 | 76 | 77 |
| Total checkpoints previos | **227** | **231** |

305/458 obtuvieron H4 proxy válido (**66,6%**). Al restringir a los dos estados `RECLAIM/ACCEPTED` empleados por la interacción hay **282 casos con H4 válido** (136 EUR y 146 GBP), de **424 casos R/A originales** (EUR: 94+115=209; GBP: 92+123=215): **282/424=66,5%**. No imputar los 142 restantes; advertir sesgo de selección por disponibilidad de H4.

| Célula E2, H4 válido | RECLAIM — reversión | ACCEPTED — reversión |
|---|---:|---:|
| EURUSD H4 alineado | 12/34 =35,3% | 25/54 =46,3% |
| EURUSD H4 opuesto | 12/26 =46,2% | 6/22 =27,3% |
| GBPUSD H4 alineado | 13/39 =33,3% | 27/53 =50,9% |
| GBPUSD H4 opuesto | 6/26 =23,1% | 9/28 =32,1% |

Las cuatro celdas de cada estrato usado tienen N≥10 (mínimo 22). Estas tasas son **exploratorias**; hay posible interacción 3-vías entre estado/mercado/H4, NO hallazgo suficiente para tradear.

### Comparación correcta sobre la MISMA muestra

| Contraste entre pares | Diferencia |
|---|---:|
| Original todas las 424 RECLAIM/ACCEPTED | **+22,38 pp** |
| Solo 282 con H4 proxy válido, sin ajustar | **+14,42 pp** |
| **Mismos 282, estandarizado por H4 con pesos comunes** | **+14,33 pp** |
| Bootstrap IC95 interacción E2 estandarizada | **[−5,97,+32,54] pp** |

Pesos H4 comunes: alineado **63,83%**, opuesto **36,17%**. **Efecto de estandarizar H4 sobre muestra idéntica ≈ −0,10pp, no una reducción material de 50%.** La caída de 22,38 a 14,42pp ocurre al excluir las fechas cuya H4 no satisface cobertura; **NO adjudicar esa caída a la tendencia H4**. El CI95 E2 cruza 0, así que la divergencia NO queda confirmada dentro de la submuestra H4 disponible. Tampoco queda falsada: efecto puntual positivo con incertidumbre mayor y 33,5% de estados R/A sin H4 adecuado. Bootstrap 2.000 bloques de cinco fechas comunes; las 2.000 réplicas tuvieron soporte.

## 4. Conclusión científica

**A:** la divergencia EUR vs GBP sobrevive al bootstrap temporal del histórico original (+22,38 pp, IC95 fuera de 0) y merece atención, pero no autoriza construir un trader. **B:** la H4 observada con calidad mínima **no explica de manera simple esa diferencia**, porque estandarizar H4 sobre el MISMO subconjunto apenas cambia la interacción (+14,42 → +14,33 pp); sin embargo, el intervalo cruza 0 tras excluir 142 observaciones y no permite inferir causalidad ni generalización. **No** concluir que H4 no importa o que se demostró una diferencia invariante.
**Cierre:** los proxies CISD/MSS no demuestran regla TTrades exacta, el `sweep` simple ronda 96,6% base-rate y SMT sigue sin contrastar. El próximo experimento informativo debe ser un test **SMT causal EURUSD↔GBPUSD preregistrado**, sincronizando rango y primera ruptura sin lookahead, preservando las 458 rutas. Sin SMT implementado en E1/E2. Sólo GitHub / Trader Lab; V49, DCVC, Master Frame, MT5, VPS y producción intactos; no certificación.
