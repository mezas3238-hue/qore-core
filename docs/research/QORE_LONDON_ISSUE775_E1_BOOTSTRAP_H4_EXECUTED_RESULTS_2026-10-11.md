# Londres E1 — EURUSD/GBPUSD Divergencia RECLAIM/ACCEPTED y H4 causal

**Fecha 2026-10-11 · ESTADO: TEST A EJECUTADO, TEST B H4 STRICT BLOCKED por cobertura del feed**. Análisis exploratorio sobre el mismo histórico ya consultado; NO señales nuevas, PF, stops, targets, BID/ASK, certificación ni live.

[Run E1 #38152004136 — 4/4 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38152004136) · [PR DRAFT #780](https://github.com/mezas3238-hue/qore-core/pull/780). Código ensayado SHA `c8d6c39e539423131f346f1f90f5c527fbf648ec`. Prerregistro publicado **antes del análisis** commit `8d76bab91c38caa8517499ad8629d47b46314541`.

## Test A — Interacción EURUSD vs GBPUSD, bootstrap compartido por jornadas

Los resultados originales congelados de [run #38150980682](https://github.com/mezas3238-hue/qore-core/actions/runs/38150980682) fueron conciliados y NO recalculados: 261 jornadas NY × 2 mercados, 227 EUR y 231 GBP checkpoint válido; subconjuntos:
- EUR RECLAIM: 38 REVERSAL / 94 = 40,43%; EUR ACCEPTED: 40/115=34,78%; **D_EUR=+5,64 pp**.
- GBP RECLAIM: 22/92=23,91%; GBP ACCEPTED: 50/123=40,65%; **D_GBP=−16,74 pp**.
- **Interacción E1 D_EUR − D_GBP = +22,380286 pp**, IC95 bootstrap circular de **2.000 remuestreos de 5 jornadas NY comunes**, seed 77520261012: **+7,336463 a +36,908263 pp**, 2.000/2.000 con soporte, proporción de remuestreos I<=0 = **0,001**.
- Contraste secundario tasas simples RECLAIM EUR vs GBP: +16,512488 pp; IC95 [+3,779343,+28,119594] pp, mismo remuestreo, no efecto causal.

Este resultado **restringe** la posibilidad de ruido muestral simple bajo el procedimiento usado; NO es confirmatorio ni out-of-sample: periodos reutilizados y fuente temporal compartida, regímenes de activos correlacionados y grados de libertad de diseño. No autoriza filtros ni tratar el estado como regla de entrada universal.

## Test B — H4 antes del raid, estrictamente reconstructible, NO evaluable

Prerregistro exigía tres barras H4 UTC COMPLETAS anteriores al raid: **720/720 velas M1** observadas en 12h, cerradas antes del raid. Fuente native-M1 original. **Resultado**: EUR 227/227 y GBP 231/231 `H4_UNKNOWN_GAP`; 0 clasificación H4 alineada/opuesta en las 458 señales. Por ello:
- H4 interacción ajustada = `null`, 0 observaciones verificables.
- H4 bootstrap 0/2.000 cálculos válidos; CI95 `null`.
- No es evidencia de ausencia o irrelevancia de tendencia H4, ni falsación de H4 como modulador; es una limitación de cobertura/representación M1 con definición estrica 720/720, **no permite la segunda prueba sustantiva**.
- No "arreglar" borrando jornadas ni haciendo forward-fill o marcando velas incompletas como completas. El código deja `first missing M1 timestamp` como testigo por trade en los artefactos, y NO reconstruye H4 a posteriori desde el cierre futuro.

Si se necesita volver a intentar H4, **nuevo protocolo independiente** y etiquetado, por ejemplo barras H4 con cierre observado y límite explícito de frescura, cantidad de M1 por bucket/hora y múltiples sensibilidades predefinidas, o velas H4 nativas certificadas, todo `PROXY_OBSERVED_H4`, nunca `STRICT_H4` ni regla autoral. No elegir tolerancia por retorno económico ni sobre la base de estas tasas.

## Estado y prioridades

El simple primer barrido Asia high/low ocurre ~96,6% de jornadas completas bajo reloj NY del autor interpretado con DST, por lo que NO es selector rentable por sí mismo. **La interacción condicional RECLAIM/ACCEPTED entre EUR/GBP sobrevive al bootstrap temporal de cinco jornadas**, pero todavía NO sabemos si la responsable es composición de regímenes H4, volatilidad o dependencia estructural del proveedor. No inferir que un par 'manipula' y otro 'continúa' de forma intrínseca.
SMT es la próxima hipótesis independiente lógica, sin alterar las 458 rutas ya congeladas ni construir trader. E1 no testea SMT; CISD original aún sin equivalencia demostrada. No Asia/NY, no MT5/VPS/live, V49/DCVC/producción intactos.
