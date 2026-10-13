# ADR-QN-2026-10-12-01 — Cierre de investigación FX Carry y cambio a decisión arquitectónica

**Estado: DECISION FIRMADA COMO RECOMENDACIÓN TÉCNICA, NO APROBACIÓN OPERATIVA**  
**Fecha de la decisión: 12 octubre 2026 (Paraguay); evidencia Action final 13 octubre UTC**  
**Responsable de investigación: arquitecto metodológico; aprobación efectiva de prioridades/recursos: propietario/COG/OPS según gobernanza QORE.**

## Decisión inequívoca

**Elegir opción C PARA EL ALCANCE ACTUAL DE QORE NATIVE**: suspender la búsqueda adaptativa de rentabilidad de FX carry y registrar que esta configuración —33 instrumentos mayoritariamente FX, series spot/CFD, costes supuestos y fuentes de política monetaria— **no ha demostrado un edge neto y certificable** bajo los ensayos ejecutados. La conclusión **NO** implica que QORE como plataforma sea incapaz de captar edges ni que el carry de divisas universalmente carezca de rentabilidad.

**Queda formalmente congelada la línea de modelos FX carry en el universo actual**: H4 `BLOCKED_NOT_TESTED` (forward verdadero 1M sin quotes PIT); H5 `EXECUTED_SPOT_NO_POSITIVE_SUPPORT_IDEAL_EXPLORATORY`; H6 (2010–15) `BLOCKED_SOURCE`; H6a `EXECUTED_NO_PROMOTION_EXPLORATORY`; **H6b `CLOSED_NOT_EXECUTED_NO_RESCUE`**. No ejecutar H6b (21 cruces no-JPY, 2010–15) ni H6c, no retunear vol20, target, 6L/6S, temporización, fuente BIS, coste ni métrica en 2022–24. No consumir económicamente el holdout sellado desde 2024-09-17.

**NUEVAS MISIONES A/B no se autorizan automáticamente**. Una nueva misión deberá obtener consentimiento explícito del propietario y un preregistro nuevo antes de fijar universo/etiquetas/criterios, demostrar fuente y costes suficientes desde el arranque, y separar los test de decisión de las pruebas de evaluación.

## Hechos cuantitativos observados, no supuestos

| Ensayo | Estado, universo | DEV | DIAG | Validez y limitación |
|---|---|---:|---:|---|
| H1 TSMOM20 | ejecutado 33 CFD/spot | Sharpe diario anual −0.09199 | **−0.27205** | no soporte |
| H2 TSMOM252 vol20 | ejecutado 33 CFD/spot | Sharpe diario anual −0.05084 | **+0.07669** | débil y no confirmado |
| H3 XS REV 5d | ejecutado 33 CFD/spot | Sharpe diario anual +0.24788 | **−0.50706** | no soporte |
| H4 FX forward carry 1M auténtico | sin datos forwards históricos PIT | N/A | N/A | **NO probado**, nunca calificar como resultado económico negativo |
| H5 carry BIS política 6L/6S, 2bp/side | ejecutado 28 FX, DIAG previamente expuesto | **Sharpe spot −0.28458; B ideal −0.01809** | **Sharpe spot −0.17504; B ideal +0.31349** | *B* añade financiación política IDEALIZADA, sin swaps ejecutables |
| H6 extension 2010–15 | source gate | N/A | N/A | BIS JPY: 32 meses 2013-05→2015-12 ausentes; muestras Dukascopy **27/56** verificadas, 29 indeterminadas |
| H6a BIS+vol global20 y Sortino | ejecutado 28 FX, **mismo DIAG adaptativo** | **Sortino spot −0.52796; B ideal −0.14358**; CAGR B −0.7961% | **Sortino spot +0.03344; B ideal +0.80722**; CAGR B +2.88678% | criterio múltiple de preregistro FALLA: media mensual B bootstrap bloques6 IC95 **[−0.28992%, +0.81913%]** cruza cero. Skew B DIAG −0.351, MDD −7.378%, ES5% −3.169%, peor mes −4.464% |

*H5 presenta Sharpe anualizado de retornos diarios mientras H6a presenta Sharpe anualizado de retornos mensuales.* No comparar 0.313 y 0.509 como estimadores idénticos, ni llamar a su diferencia “corrección de edge”. H6a DIAG tiene 33 meses; DEV 64. **B idealizado no es beneficio broker NET**. Las dos estrategias H5/H6a comparten datos y señal y NO constituyen réplicas independientes de carry. Test H4 forwards auténticos **nunca fue económicamente ejecutado**; el preflight es una decisión de fuente, no un tercer carry negativo.

**Deber científico de evitar frases erróneas:**
- No decir que H6a tiene Sharpe significativamente positivo. Sharpe 0.509 **anualizado** sobre 33 meses, SE aproximado `sqrt(12/33)=0.603` si IID y Sharpe pequeño; IC orientativo `0.509±1.96×0.603≈[−0.67,+1.69]`. El cálculo `1/sqrt33≈0.174` corresponde al error de escala **mensual** y no puede aplicarse directamente a Sharpe anual 0.509. Distribuciones con colas/autocorrelación y selección adaptativa exigen cautela; bootstrap 6m/12m de H6a es más directamente pertinente, aunque no elimina selección de hipótesis.
- DEV B negativo no es prueba lógica de ausencia universal de carry (varía la prima de riesgo por regímenes), pero rechaza la afirmación **de robustez replicada entre periodos en esta configuración**.
- No extrapolar H6b: que H6a falle NO demuestra que 2010–2015 siete divisas produciría necesariamente menos retorno. La decisión de no financiar H6b es de **rendimiento marginal de investigación y disciplina contra rescate adaptativo**, no un resultado empírico de H6b.
- No sostener que Sortino corrige skew negativo. Sortino MAR0 >0.5 puede coexistir con riesgo de crash; documentar drawdown, ES, peor mes, sesgo, volatilidad y costes de financiación.
- No afirmar que 28 FX equivale a 28 riesgos macro independientes: son ocho monedas con siete factores relativos de tipo cambio lineal.
- No afirmar causalidad económica de 2026-revisado BIS policy rates sin as-of vintage; 2 meses de lag atenúan pero no eliminan revisión ex post.
- No afirmar que ausencia de historical forwards implica no poder operar carry teóricamente; implica falta de test del carry **realmente liquidable** con la evidencia actual.

## Tres salidas arquitectónicas: decidir ahora, no iterar estrategia

**Opción C — ADOPTADA PARA LA ETAPA ACTUAL:** documentar la frontera empírica y separar la infraestructura Trader Lab (reutilizable) de la promesa de rentabilidad. Mantener bibliografía, hash de fuentes, 28 M5, 8 BIS policy and datos de calidad para otros estudios; **cero traders nuevos certificados** y cero autorización CIBO/cognitiva por las pruebas de carry. No nuevas variantes de la misma familia con DIAG ya observado. **No exige nuevo proyecto de datos**.

**Opción A — POSIBLE NUEVA MISIÓN DE ADQUISICIÓN, NO APROBADA:** sustituir o ampliar universo hacia acciones líquidas o futuros verdaderos no-FX (con estructura de contratos, roll, financiación, bid/ask y riesgo), no solo 5 CFD índices/metales. Antes de cualquier PnL: disponibilidad histórica limpia, snapshots predecisión, derechos de uso, costes y presupuesto; preregistro con n hipótesis cerradas. Es una decisión de inversión en datos distinta de retocar el modelo FX.

**Opción B — POSIBLE NUEVA MISIÓN CAUSAL, NO APROBADA:** estudiar **flujos exógenos / forzados** (rebalanceos públicos de índices, roll de futuros, vencimientos, subastas e impactos medibles con timestamp as-of). Requiere evidencias de un disparador PREDECISIÓN e instrumento capaz de capturar flujo después de costes. No usar velas OHLC como sustituto de order-flow no observado ni introducir 100 proxies en vez de una hipótesis. En caso de carecer de datos verificables, **NO START**.

**Orden de inversión recomendado:** C ahora. No iniciar A ni B por inferencia de que “deben ser rentables”; antes exigir del propietario de QORE una autorización específica de datos/alcance y preregistro. Si una misión independiente se autoriza, elegir A o B sobre la base de **calidad de datos disponibles para la hipótesis**, no de la búsqueda de un Sharpe por exploración no acotada.

## Gobernanza y entrega de esta decisión

- H5 referencia canónica [PR #887](https://github.com/mezas3238-hue/qore-core/pull/887), [resultado Actions #38324559982](https://github.com/mezas3238-hue/qore-core/actions/runs/38324559982) y reporte `docs/research/QORE_NATIVE_H5_POLICY8_FX28_2BP_EXECUTED_SPOT_NEGATIVE_IDEAL_WEAK_2026-10-13.md`.
- H6 histórico fuente [PR #888](https://github.com/mezas3238-hue/qore-core/pull/888), [Actions #38326759354](https://github.com/mezas3238-hue/qore-core/actions/runs/38326759354), reporte `docs/research/QORE_NATIVE_H6_2010_POLICY8_DUKA28_SOURCE_GATE_EXECUTED_BLOCKED_2026-10-13.md`.
- H6a [PR #890](https://github.com/mezas3238-hue/qore-core/pull/890), [Actions #38328728365](https://github.com/mezas3238-hue/qore-core/actions/runs/38328728365), documento `docs/research/QORE_NATIVE_H6A_FX28_VOL20_SORTINO_CRASH_EXECUTED_NO_PROMOTION_2026-10-13.md`.
- H4 1M forwards solo data gate [PR #883](https://github.com/mezas3238-hue/qore-core/pull/883), [issue #884](https://github.com/mezas3238-hue/qore-core/issues/884); ya no es prioridad de optimización FX-carry, conservar custodia de hallazgos.
- Handoff maestro canónico [PR #855](https://github.com/mezas3238-hue/qore-core/pull/855), **recibe enlace explícito a este ADR**. Evidencia de Actions artefactos expira alrededor de noviembre 2026; el resumen, exact code SHA y checksums de cada reporte deben mantenerse dentro del repositorio, sin copiar raw de precio/tasas con licencia al repo.

## Criterio de reactivación

No reabrir FX carry mediante “H6b/H6c” o un filtro cercano. Sólo reconsiderar la *familia* si existe **nuevo hecho material EXTERNO** previamente no disponible: fuente forward/swap broker auténtica PIT multiannual con costos reales y una ventana prospectiva genuinamente no utilizada, o mandato explícito con un universo y mecanismo radicalmente distintos. Cualquier examen así lleva nuevo comité/prereg y no toma DIAG H5/H6a como validación independiente.

**No tocar LIVE, MT5, VPS, CIBO, Shared, cognitiva, QDLE ni QORE production; no abrir holdout desde 2024-09-17.**

**Dictamen final del arquitecto metodológico: QORE Native actual = 0/3 nuevos traders certificados; carry FX R&D FROZEN / NO PROMOTION; opción C ACTIVA para la investigación, sin asumir aprobación administrativa que corresponde al propietario.**
