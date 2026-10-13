# QORE Futures A — cierre de la única prueba preregistrada EIA WTI/NG F1/F2

**Fecha:** 2026-10-13. **Evaluación: NO_SUPPORT_UNDER_PREREG para las dos hipótesis específicas.** No constituye NO_EDGE, falsación general de estrategias de commodities, resultado financiero, backtest ni trader certificado.

## Cadena íntegra de evidencia

- Preregistro publicado **ANTES** de leer las respuestas: [QORE_FUTURES_A_EIA_WTI_NG_F1F2_PREDICTIVE_SCREEN_PREREG_2026-10-13.md](QORE_FUTURES_A_EIA_WTI_NG_F1F2_PREDICTIVE_SCREEN_PREREG_2026-10-13.md), commit **`00065e6df7450cac707f983858ca39eed7b30c47`**.
- Código exacto `src/qore/infrastructure/trader_lab/qore_futures_a_eia_f1f2_predictive_screen_v1.py` con Fisher unilateral **exacto** calculado mediante distribución hipergeométrica combinatoria en Python stdlib (matemáticamente equivalente a scipy.stats.fisher_exact), sin agregar modelos ni parámetros.
- [GitHub Actions #38448311219 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38448311219), HEAD de la ejecución `25b8d2fc18c02992ff1115bbb117cc42438de891`, **8/8 tests sintéticos PASS**.
- [Artefacto JSON de resultados #11839586948](https://github.com/mezas3238-hue/qore-core/actions/runs/38448311219/artifacts/11839586948), SHA256 del ZIP `48cc8c7e8b3816fb7adf23658303bd90c3ed9e270c6e0e015fbd82a9904bf9eb`, retención 90 días a partir de 2026-10-13; guardar referencia y rerun reproducible por workflow si expira.
- Cuatro XLS EIA de 2012 a 2024 auditados y SHAs verificados en el pipeline, cero compras, cero credenciales y ninguna operación; runner descartó observaciones `>=2022-01-01` antes de crear retornos y señales de prueba.

## Hipótesis y medida (congeladas antes de ejecutar)

Cada mes, **la primera fecha común** del contrato-rango F1 y F2: `backwardation = F1(t) > F2(t)`; evaluar si `F1(t+7) - F1(t+2) > 0` usando hasta la octava fecha común del **mismo mes**. Ties de precio o spread excluidos. Un dato mensual por root; resultado = diferencia de probabilidades `Pr(subida | backwardation) – Pr(subida | contango)`. Evaluación unilateral Fisher, familia WTI/NG Bonferroni **p <= 0.025 por root** en **ambas** ventanas, delta >= +0.10 en ambas y >=8 meses en cada estado por ventana. Ninguna otra señal, duración, activo, horizonte ni reversal probado. Sin licencias de MDP3, nativos de vencimiento, as-of publication histórico o costes ejecutables.

## Resultados exactos en el acta

| Root | Ventana | N meses válidos | N backwardation | N contango | Positivos backwardation | Positivos contango | Diferencia Pr(up) | p Fisher unilateral |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| WTI | DEV 2012–18 | 83 | 22 | 61 | 10 | 30 | **−0.0372578241** | **0.7077117236** |
| WTI | DIAG 2019–21 | 36 | 14 | 22 | 12 | 14 | **+0.2207792208** | **0.1444197256** |
| NG | DEV 2012–18 | 83 | 14 | 69 | 3 | 43 | **−0.4089026915** | **0.9992107844** |
| NG | DIAG 2019–21 | 35 | 10 | 25 | 8 | 11 | **+0.3600000000** | **0.0579600229** |

- 120 meses DEV+DIAG posibles por raíz; WTI 119 eventos válidos, uno excluido porque `F1(t+7)-F1(t+2)=0`; NG 118 eventos válidos, 2 meses excluidos por `F1(t)==F2(t)`. Cada estado supera el mínimo prereg de 8 meses por ventana.
- En **DEV** la hipótesis tiene delta **negativa** en ambos mercados; en **DIAG** positiva pero no significativa al umbral **0.025** y no reproduce DEV. **No promoción** en ambas hipótesis. No cambiar la dirección ex post a "contango predice subidas" ni filtrar años para rescatar la asociación.
- Reportes por root del runner usan `decision=NO_POSITIVE_DIRECTION` porque DEV delta<=0, y DIAG `NO_SUPPORT_UNDER_PREREG`. El dictamen económico-científico completo es **`NO_SUPPORT_UNDER_PREREG` / NO_HOLDOUT_PROMOTION**.
- El holdout de EIA **2022–2024-04** se mantuvo **sin observar outcomes**, y el holdout independiente original FX **desde 2024-09-17** igualmente sellado; no se permite usar la reserva automáticamente tras FAIL.
- (p=0.058) de NG DIAG **no** es significativo tras corrección: es una pista no confirmada que cambia de signo DEV, no nueva hipótesis autorizada.

## Limitaciones científicas que NO se pueden omitir

1. EIA F1/F2 son **rangos móviles de delivery** sin identidad de vencimiento. Seleccionar fechas tempranas de mes reduce, **no elimina**, cambios de contrato o calendario. La variable respuesta mide diferencia de precios de referencia, **NO retorno real de un futuro ni retorno de la pendiente**.
2. El timestamp de **publicación histórica as-of** no fue demostrado; el lag preespecificado de dos observaciones NO sustituye esa prueba. Aun el desarrollo/diagnóstico es **exploratorio no ejecutable**.
3. Con ~35 meses DIAG por activo y clases asimétricas el test tiene potencia limitada; fallo no prueba inexistencia de todo edge. No hay volumen/OI contract-native, spread, clearing, comisiones, deslizamiento, ni cost model.
4. Ningún resultado con ventaja positivo incondicional autoriza transacciones. CIBO, Traders FX, Shared, MT5, VPS, LIVE, capital real, QDLE, y holdout permanecen fuera de alcance.

## Decisión y estado de investigación

**Para esta hipótesis específica: STOP / NO_SUPPORT_UNDER_PREREG**; no nuevas ventanas, direcciones, roles de contratos o horizontes como iteraciones sobre el mismo diagnóstico. **SOURCE_M0 para seis futuros sigue `BLOCKED_DATA_OR_LICENSE` con US$0**, pero conseguimos evaluar provisionalmente esta única asociación en dos mercados sin pagar.

**Ningún nuevo trader certificado; 0 PnL.** La propuesta de examinar holdout no se activa porque el protocolo falló DEV y DIAG. Nuevos ensayos requieren mecanismo realmente diferente, preregistro nuevo y evidencia genuinamente nueva; no se promueve el mismo predictor con la dirección invertida porque se ha visto el resultado.
