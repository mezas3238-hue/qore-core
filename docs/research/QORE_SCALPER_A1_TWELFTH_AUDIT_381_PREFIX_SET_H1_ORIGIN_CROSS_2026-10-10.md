# Trader Scalper — Duodécima auditoría: CISD as-of observable versus first selector no causal + H1 C2/C3

**Fecha:** 10 octubre 2026, proyecto QORE Scalper. A1 cognitive PR #758 DRAFT, A2 metodología PR #759 DRAFT y maestro #623 DRAFT. Exclusivamente GitHub, **NO VPS/LIVE/MT5/merge/certificación**. Esta no es construcción del World Model: se verifican artefactos ya producidos por B, sin código cognitivo ni gates nuevos.

## P0-1 | Pregunta del auditor en sus dos significados distintos

> Para cada una de las 381 discrepancias, ¿la CISD original V49 era identificable con las velas M1 cerradas disponibles en la decisión? ¿Era además la PRIMERA señal que elegiría la política causal online entre las dos rutas?

**Respuesta auditable, únicamente para los dos observadores V48/QORE, no prueba universal de TTrades:**

| Estado al cierre de vela M1 fuente | N de 2.876 | En las 381 |
|---|---:|---:|
| Original V49 es primer CISD confirmado de SU PROPIA ruta en prefijo M1 (testigo constructivo de pertenencia) | **2.876** | **381 IN_QORE_OWN_ROUTE_PREFIX_SET** |
| Original V49 es el primer evento GLOBAL entre Sweep/FVG en prefijo M1 | **2.495** | **0** |
| Original V49 NO es el primer evento global ONLINE seleccionado en el prefijo M1 | **381** | **381** |
| Original V49 ausente del prefijo en su propio detector | **0** | **0** |
| Concordancia completa con alineación de POI/swing TTrades original | **NO DEMOSTRADA** | **NO DEMOSTRADA** |

Los 381 no constituyen «381 cierres CISD físicamente imposibles de observar». Son **381 selecciones offline de primera ruta no prefix-invariant**. La reproducción V49 con ventana de investigación completa y la ejecución prefijo con corte en cierre original dan primera ruta diferente. La ventana retrospectiva puede incorporar M1 futura del instante de decisión; por tanto el **criterio de first selection en replay V49 está contaminado como selector online**, aunque la misma CISD pueda ser observable en la rama original. Para una «CISD inexistente en el conjunto completo de reglas TTrades» se necesitaría enumeración exhaustiva de POI+swing+serie con prueba fuente del autor; **no inferir el hecho contrario de la ausencia de un censo universal**.

**Evidencia primaria de programación B:**
- [#38095562104](https://github.com/mezas3238-hue/qore-core/actions/runs/38095562104): mismo observador Sweep y FVG sobre ventana completa reproduce V49 2.876; sobre prefijo cerrado a fuente decision reproduce sensor 2.876; 381 selecciones diferentes.
- [#38096548896](https://github.com/mezas3238-hue/qore-core/actions/runs/38096548896): primer evento **en ruta propia** del prefijo coincide exactamente con el cierre de V49 **2.876/2.876**, a pesar de 381 conflictos globales. Artifacts source-ID, nueve mercados. B marca honestamente `original_absent_from_all_asof_candidates=null` para recordar que **NO** enumera todas las rutas TTrades posibles; esa incertidumbre no borra el testigo positivo de existencia en ruta QORE.

**Nueva segunda opinión ejecutada por A1**, [GitHub Actions #38098618743 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38098618743): descarga directamente 9 artefactos prefijo B #38096548896 (SHA `aff644d548558749c47cda7fb4062a538f00845c`), 9 artefactos H1 B #38096345552 (SHA `56b3c3b9970e1b02e9b5337a06a40c2bdf98cd06`) y 9 libros V49 congelados #38053946695 SHA `e356e7a52541e99533b25ecfef0ab9c4e9ce03c0`. Conciliación independiente hash 2.876 IDs, `source_entry_at`, `family`, fuente H1 `h1_state_basis` + `h1_state_from`, y flag de selección online. **No usa resultados MFE/MAE ni input futuro de precios**. Una única GitHub Action con Python inline, **sin crear motor ni dependencia de trading**; resultados JSONL de 2.876 ID y JSON agregado como artifact.

### P0-2 | H1: 8,3% es uso C3, no «8,3% fidelidad»

La fuente [TTrades, TTrades Scalping Model (7 febrero 2026)](https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/) utiliza explícitamente cierre H1 **Candle 2 o Candle 3**; [TTrades, How CISD Confirms Swing Points (10 enero 2026)](https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/) exige después asociación entre el swing/POI que formó el extremo y CISD LTF con cierre HTF. **El 8,3% C3 por sí solo no es una medida de fidelidad ni de ausencia de C2.**

En original V49 hay:
- **2.638 CANDLE2_REVERSAL** = 91,7%.
- **238 CANDLE3_CONFIRMATION** = 8,3%.
- **1.604 SESSION_INHERITED H1** = 55,8% (firma de cierre heredada de un estado H1 previo, no necesariamente evento HTF nuevo en la sesión actual).
- **1.272 H1 STATE_BEGAN_AT_EVENT** (no heredados).
  
Estos N etiquetan **el origen del sesgo declarado por V49**, no certifican 2.876 POIs originales ni prueban que C2 de QORE coincide para todos los trades de TTrades. El generador QORE H1 usa el modelo propio de C2 reversal y C3; falta inspección fuente primaria **por evento H1, su POI causal y qué implica «H1 bias still valid» cuando se hereda en la sesión siguiente**.

### P0-3 | Cruce independiente entre discrepancias CISD y procedencia H1

Nueva medición de [#38098618743](https://github.com/mezas3238-hue/qore-core/actions/runs/38098618743), **2876/2876 ID conciliados**:

| Estado first-selector CISD | H1 C2 original | H1 C3 original | Total |
|---|---:|---:|---:|
| GLOBAL_FIRST_PREFIX_MATCH | 2.283 | 212 | **2.495** |
| OFFLINE_FIRST_NOT_PREFIX_INVARIANT | **355** | **26** | **381** |
| Total | **2.638** | **238** | **2.876** |

**Estratificación simultánea (CISD non-prefix-invariant 381):**
- C2 no heredado 157, C2 heredado **198**.
- C3 no heredado 7, C3 heredado **19**.
- **217/381 heredados**, **164/381 no heredados**.

**No hay licencia estadística para atribuir causa a C2 o C3**. La discrepancia aparece en ambos grupos; la herencia está sobre-representada dentro de esos 381 sólo ligeramente respecto a su base. Sin control de mercado/sesión/POI y contrafactual preregistrado, eso es descriptivo y no explica el selector offline.

## Estado epistémico y próxima investigación obligatoria (B)

**Cerrado a nivel ingeniería QORE:** P0 de existencia de la CISD original al cierre en su propia ruta = **381/381 IN_QORE_PREFIX_SET**; número de eventos de la ruta propia no detectables = 0. **Cerrado causal selector negativo:** 381/381 primeras selecciones globales de V49 no reproducidas online. **NO autoriza reparar a ciegas** la prioridad del selector ni usar una ruta anterior de la familia alternativa como entrada: tendría que probar POI/swing/HTF, SL/TP y costes.

**Abierto:**
1. **B adjudicar mecanismo exacto del selector offline:** por qué `_earliest_m1_trigger` sobre un *deadline* M15/H1 retrospectivo y observadores Sweep/FVG puede elegir otro evento que la evaluación causal de prefijo. Ejemplo paso por cierre M1 para las 247 early + 134 same-time con timestamps de precursor/confirmación y desempate; clasificar regla de precedencia como **QORE_ENGINEERING_RULE**, no fidelidad literal TTrades, si ambas rutas satisfacen el autor.
2. **B verificar H1 fuente por POI/wick/swing:** en especial 1.604 estados heredados, los 2.638 C2, 238 C3 y semántica de confirmación HTF; no afirmar que C2-label supone fidelidad 91,7%.
3. **B A/B C3 dic-2025 vs ene-2026:** considerar estratos **2495 prefix-first concordantes** y **381 first-selector no causal** POR SEPARADO; reportar población propia de cada rama, intersección, +30m y cobertura causal nativa, y sólo después replay PAPER verdadero sin usar V49 offline first global para decidir.
4. **A1** mantiene congelado Global World Model, regímenes y adición de authority al Master. Conserva frontera sin futuro, sensores e inputs físicos para futuro replay, sin añadir nuevo gate ahora.
5. **Económico y certificación:** 2876 fuente V49, 2020 trades PAPER baseline, PF 0.66446 DD 236.13R **no certificados causalmente** si política first global difiere en 381; no hay PF/DD nuevo, fees BID/ASK ni repliegue correcto. NO CERTIFICABLE / NO LIVE/VPS/merge.

**No prohibimos los 381 como filtro** (la abstención histórica empeoró PF/DD); tampoco alteramos la prioridad online hasta evidencia fuente/salida, y ningún resultado de este atlas aporta edge monetizable.
