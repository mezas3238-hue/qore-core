# VT08 CRT PURE — CAMBIO VINCULANTE DEL OWNER: CRT DE TRES FUENTES (15-OCT-2026)

**REPOSITORIO** `mezas3238-hue/qore-core` · **PR #626 DRAFT** `agent/vt08-crt-pure-source-identity-001`. NO MERGE, NO VPS/DEMO/LIVE/órdenes, NO SIZING del Trader. **CIBO/QORE Risk** monopoliza volumen y capital.

## Orden Owner 15-OCT prevalente

> El Trader CRT **no necesita ser exactamente fiel a RomeoTPT**. Hay TRES fuentes disponibles y debe certificar la metodología y cognitiva con un CRT coherente construido desde esas fuentes. No detener la investigación esperando una prioridad «old CRTH» atribuible sólo a Romeo. **Avanzar hacia TODAS las certificaciones**, incluyendo Profit Factor, Drawdown, Sharpe, Sortino y demás Gates económicos vigentes.

Este cambio **sustituye el veto técnico «Romeo-only Model #1 source ready»** como precondición específica para la **certificación de un CRT QORE compuesto**, pero **NO altera retrospectivamente** el hecho histórico de que cierto concepto original Romeo es ambiguo. `model1_source_ready()` del registro del autor puede seguir False; no falsear CANONICAL en el registro histórico. Es una **NUEVA IDENTIDAD de método QORE** y requiere evidencias propias.

## Tres fuentes autorizadas y límites de sus aseveraciones

1. **RomeoTPT:** fundador/crt original. [Base](https://www.youtube.com/watch?v=UUq_wKQ61Wo), [old CRTH post](https://t.me/s/officialRomeotpt/6615).
2. **SpeculatorFL:** [CRT multi-protocol thread (28-APR-2024)](https://threadreaderapp.com/thread/1784493604473618604.html) respalda ranges H/L/O/C, purga de lado, micro CRT en HTF, inside bars, CSD y objetivo 50%/lado opuesto.
3. **TraderFlameseN:** [Choose Best CRT Candle (13-MAY-2024)](https://threadreaderapp.com/thread/1790141530461622525.html) respalda los temas análogos, créditos a Romeo. **Textos 2 y 3 casi paralelos; NO son dos pruebas econométricas independientes.**

**Resolución QORE:** documentación fuente individual o síntesis `OWNER_APPROVED_QORE_ENGINEERING` CON explicación y revisión. No inventar reglas con el PnL. No reatribuir ingeniería a los autores. No imponer simultáneamente filtros opcionales de tres escuelas que causen densidad ridícula.

## Código efectivamente modificado

- `crt_pure_three_source_methodology.py`: política **`VT08_CRT_THREE_SOURCE_QORE_V1`**, fuentes permitidas y siete contratos (referencia, prioridad multirreferencia, HTF/LTF, confirmación, invalidación, destino, conflictos/rearm). El contrato `SOURCE_SUPPORTED` debe constar en el registro de evidencia con concepto y URL EXACTOS; `OWNER_APPROVED_QORE_ENGINEERING` requiere registro Owner y justificación. Hoy reglas operativas **OPEN**, no certificar.
- `crt_pure_methodological_certification.py`: ahora comprueba **política tri-fuente QORE** y los cuatro Gates cualitativos, NO `model1_source_ready()` Romeo-only.
- `crt_pure_certification_readiness.py`: certificado GLOBAL usa **composición tri-source** para identidad, sigue exigiendo mercado/replay/OOS/WFO/MC/stress/validación independiente; no autorizaciones económicas.
- `crt_pure_r2_entry_router.py`: ruta de certificación bloquea sólo cuando falta contrato **QORE tri-source**, no porque Romeo no resolvió el caso. Oposición parent M15 continúa `ABSTAIN`; no C3 fallback ni capital.
- `vt08_crt_pure_gm3_real_case_safety.py` y tests: verifican en los 48 casos que ausencia de contratos explícitos mantiene WAIT/ABSTAIN e impide inyectar falsos PASS.

### Metodología operacional concreta propuesta y dos etapas de aprendizaje

- [**V1 pre-registrada**](VT08_CRT_3_FUENTES_QORE_V1_PREREG_2026-10-15.md): H4 C1 previo, H4 C2 purga unilateral y close dentro, M15 C1/C2 al inicio C3, DOL midpoint H4 todavía adelante; criterio de ingeniería QORE explícito. **Full original Atlas** [run #38710923324](https://github.com/mezas3238-hue/qore-core/actions/runs/38710923324) SUCCESS (quality y dos mercados), 296.372 M5, 5.524 H4 C1/C2, **54 candidatos conceptuales** (AUDUSD 31/USDJPY 23), sin sizing ni PnL. Demasiado restrictiva para la densidad deseada. No llamar operaciones.
- [**V2 pre-registrada antes del ensayo**](VT08_CRT_3_FUENTES_QORE_V2_PREREG_2026-10-15.md): permite M15 nested 15 pares temporales de toda H4 C3; primer candidato causal independiente por parent, no rearm mismo HTF, DOL H4 midpoint con no-touch anterior, no doble sweep; **nueva identidad/version**, NO retune V1 por PnL. Revisión y corrida en laboratorio independiente. En todos los casos las horas H4 de la investigación son UTC, ingeniería QORE no regla universal Romeo.

## Lo que sigue BLOQUEANDO la certificación legítima

**G-M1:** sintetizar y adjudicar todas las reglas V2 elegidas con contratos exactos y revisión real; distinguir AUTHOR vs QORE y conflictos. **G-M2:** revisar casos reales que incluyan positivos/negativos, 48 FIRST LOOK previos sirven pero no constituyen OOS ni dictámenes; auditar nueva V2 sin mirar desenlace. **G-M3:** reconciliar V2 con cognitivas de situación/tesis/falsación y decisiones no meros ABSTAIN por fuente falta. **G-M4:** demostrar E2E fuente→cognitiva→router→expiración→CIBO external sin sizing/órdenes. **G-M5:** solo con G-M1..G-M4 PASS y evidencia genuina de firma, nunca bandera booleana.

**Economía GLOBAL:** ninguna de las hipótesis de geometría es un fill. No existe PF NET, Sharpe, Sortino o DD patrimonial CERTIFICADO para esta identidad. Se necesita una estrategia congelada **con contrato explícito de ejecución y coste original verificado**, nuevo OOS realmente intacto, WFO, stress, Monte Carlo, tamaño muestral, PF/DD/Sharpe/Sortino/expectancy, benchmarks y revisiones independientes. Definir umbrales **antes de mirar resultados** bajo autoridad Owner/Risk y no importar los de #762 (VT08 TTrades 5M distinto) o #838 (Alpha2). **Para DD patrimonial CIBO/Risk externo**, no se permite a VT08 introducir ni 1 lote supuesto ni capital normalizado.

**Custodia urgente:** [Issue #837](https://github.com/mezas3238-hue/qore-core/issues/837), Atlas12 source vence 2026-12-16; respaldo privado autorizado con SHA+restore antes de ese momento, nada de mover fuentes no licenciadas al repo público o VPS.

**ACTA:** La autorización del Owner para tres fuentes **remueve Romeo-only como veto injustificado**, no es permiso de certificación sin pasar Gates ni permiso operativo. Si el trader V2 no tiene densidad o edge suficiente en evaluación legítima, dictaminar FALLA de esa versión y continuar nueva hipótesis sin contaminar OOS.
