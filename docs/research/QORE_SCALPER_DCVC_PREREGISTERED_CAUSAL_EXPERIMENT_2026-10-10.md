# PRERREGISTRO DCVC v0.1 — QORE Trader Scalper (INVESTIGACIÓN)

**Fecha:** 2026-10-10 (America/Asuncion). **Estado inicial:** preregistrado ANTES de ejecutar ensayos DCVC. **Ambiente:** GitHub Actions / Trader Lab exclusivamente; nunca VPS/MT5/live/prod. **Rama:** `research/scalper-dcvc-causal-conditional-edge-20261010` basada en A2 SHA `bf8ce75faa6a94fbbc4c33ca74b9a15a2aa53c82`. BASELINE inmutable V49 run `38053946695`, SHA `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`; provider M1 run `35548099334`, SHA `18c338aedd5013ce65a6cb6408ffbc2e904a6217`. Etapa M1-V49 source-anchored **no demuestra el universo completo first-online**.

## Hipótesis falsables (sin promesa de edge)

- H0: condicionar las oportunidades existentes a información de volatilidad y eficiencia direccional conocida en M1 no mejora la esperanza y el DD netos frente al baseline **ni** frente a controles de igual exposición.
- H1: algunos regímenes previos a la entrada mantienen media R neta positiva en intervalos temporales verdaderamente no usados en la construcción, preservando ganadores/frecuencia. Se rechaza si los estimadores no son consistentes, el PF neto es <=1, la ventaja cae con costes o es indistinguible del control aleatorio matched.
- H2 incremental: la cognitiva Master Frame ya existente agrega señal residual causal encima de DCVC; **C permanece BLOCKED** hasta disponer de registros ejecutados y as-of, nueve percepciones reales, posición/capital y reejecución independiente; está PROHIBIDO reemplazarlo con proxy.
- Hipótesis distinta **TTRADES_M30_M3**: modelo explícito de autor 30M→3M; NO aplicar esos gatillos automáticamente a H1→M15→M1. Solo shadow/revisión y futuro A/B separado.

## Universos y control

A se reconstruye exclusivamente desde 2876 V49 opportunities y trades SOURCE originales, y `_portfolio_select` MAX3 global por sesión/fecha. Verificar exactamente N=2876, N_A=2020, wins=1167, PF bruto cercano a 0.6644630742, DD bruto 236.134284R, R=-233.269327R antes de reportar comparación. Todos los V49 IDs inmutables. B se ejecuta sobre las **mismas 2876 fuentes/intent/fills** con aceptación **previa a conocer salida**, MAX3 recalculado cronológicamente, sin crear entradas ni retocar SL/TP. La economía de B sigue V49 histórica simulada, STOP_FIRST; no constituye live physical BID/ASK. Si no llegan cotizaciones históricas sincronizadas, **neto real e incertidumbre de broker NOT_AVAILABLE**: sólo costes de estrés `0, 0.025, 0.05, 0.10R` etiquetados como suposición.

## DCVC v0.1 — features, entrenamiento y regla congelada

Variables por source-ID exclusivamente de últimas velas **provider-native M1 CLOSED <= decision_at** del símbolo: volatilidad relativa (mean(abs close-to-close) últimos 30 / últimos 240), eficiencia direccional absoluta de 30 retornos = abs(sum returns)/sum(abs returns), intensidad de desplazamiento último close en relación con media de movimientos y persistencia de signo. Ventanas suficientes: al menos 241 precios consecutivos para cálculo pleno; nada de rellenar gaps; huecos => `UNKNOWN`. Regímenes PREFIJADOS `HIGH_VOL/LOW_VOL` ratio >=1; `TREND/CHOP` eficiencia >=0.35; exactamente 4 celdas (más UNKNOWN). Precio/stop/target planificados de V49 son testigos de diseño QORE, **no fuente autor-certificada**. M30 close y M3 close calculados **solo como shadow informativo, no gate ni confirmación CISD autoral**. Spreads, comisiones sincronizadas, M30 estructura, M3 CISD verdadero, POI autor y bid/ask faltantes permanecen UNKNOWN, nunca 0 inferido ni proxy oculto.

Regla B única previamente fijada: **cold-start PASS** hasta 60 operaciones B *elegidas y liquidadas* observables antes del instante; después, para cada celda con >=20 operaciones B ya liquidadas, estimar media de R con contracción `(sum_bucket_R + 40*mean_global_R)/(n_bucket + 40)`; seleccionar SI expectativa estimada **mayor que 0.025R** (coste conservador interno), abstenerse si no. Celda UNKNOWN o n_bucket<20 => PASS informativo. No actualizar historia con trades rechazados ni con exits del futuro. No reentrenar en outcomes de otra cohorte. Este algoritmo puede suspender densidad y NO será ajustado para forzar mejorar PF. Misma decisión para cohortes, sin optimización hiperparámetros; todo negativo se publica.

## Cortes temporales y dependencia

Por cronología de entrada, desarrollo 2025-09-17→2026-09-17: primeros ~60% (hasta 2026-04-24) exploración/warmup, siguientes ~20% (hasta 2026-07-06) validación temporal, último ~20% (hasta 2026-09-17) **pseudo-test interno YA CONSULTADO**. Predicción B es prequential: a cada instante usa sólo elegidos B con `exit_at < decision_at`; no reentrena contra etiqueta del evento actual. Incluso el pseudo-test NO puede denominarse holdout independiente, porque otros trabajos QORE ya utilizaron esta misma historia. Prueba confirmatoria REQUIERE fechas nuevas o era externa nunca examinada.

Reportar A/B totales y por cortes: N, wins, gross profit/loss R, PF bruto/stress-net, mean R, DD R, winning IDs originales y winner-R, R series temporal; medio debajo máximos y rachas, frecuencia mensual/trimestral y regime. Drawdown % sólo bajo capital definido; si falta account/risk, reportar campo NOT_AVAILABLE y además escenario separado **1% del equity por R de riesgo fijo, sin leverage/limit** marcado hipotético. Medir random-matched (>=100 semillas fijas, misma cantidad aceptada por grupo operativo, usando sólo source IDs y no PnL para muestrear), y control de exposición A normalizado a fracción N_B/N_A, y fallos cuando B recorta 90% del universo. Bootstrap por días / bloque de jornadas de operación (>=300 replicaciones) sin permutar operaciones individuales.

## Guardrails y fallos

**No ganador futuro a features**, sin H1.state_until, sin MFE/MAE, ninguna vela opened/inflight, nada de spread imaginado. Entrada confirmada M1, TTL V49 intacto. Ledger separate `dcvc-predecision.jsonl` y `dcvc-outcomes.jsonl`; salida de labels nunca importada en el módulo de features. Estado de régimen calculado sólo sobre M1 anterior/cerrado; ninguna clasificación ex-post. Test monkeypatch cambia R futuro sin cambiar decisión en mismo instante. M30/M3 fuente TTrades: https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/ (30-jul-2025), ejemplo positional M3 con stop bajo EQ M30 y breaker; sin elevarlo a universal de Scalper H1/M15/M1. No merge, sin certification, sin VPS.

## Condición de éxito

La mera reducción de DD por menos operaciones no prueba ventaja; exigir conservación de PF/expectancy neta, frecuencia significativa, test independiente, aleatorio/exposición equivalente, incertidumbre y sin leak. PF<1 => perdedor neto/no certificado. Objetivos DD -25/-40/-50/-60% son sólo referencia, no criterios de selección retrospectiva.
