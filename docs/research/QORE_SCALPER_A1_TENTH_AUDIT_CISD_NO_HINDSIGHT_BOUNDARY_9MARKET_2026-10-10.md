# QORE SCALPER A1 — Décima auditoría: frontera CISD causal y aislamiento de MFE/MAE a futuro

**Estado:** P0 METHOD-FIRST / NO GLOBAL WORLD MODEL / NO LIVE. **Fecha:** 2026-10-10. **Responsable:** Cognitiva A1, [PR #758](https://github.com/mezas3238-hue/qore-core/pull/758). **Metodología primaria:** B [PR #759](https://github.com/mezas3238-hue/qore-core/pull/759). PR padre #623 permanece DRAFT.

## Resultado NUEVO y real en GitHub, sin tocar el detector

**[GitHub Actions #38094209281 — SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38094209281).** A1 procesó los 9 artifacts B del noveno experimento [#38076268436](https://github.com/mezas3238-hue/qore-core/actions/runs/38076268436), SHA del código B **1cc7b569682ec82b97fd355f5808bbc6202ef19d**, contra 9 libros de fuente V49 [#38053946695](https://github.com/mezas3238-hue/qore-core/actions/runs/38053946695), SHA **e356e7a52541e99533b25ecfef0ab9c4e9ce03c0**. Total idéntico **2876 / 2876** fuente ID hash y nueve mercados reconciliados, preservando familia, dirección H1, M15 confirmed, fecha operativa, sesión, fecha M1 y solo primeras detecciones sensor que ya ocurrieron antes/igual al cierre original.

| Taxonomía fuente/sensor confirmada | Total |
|---|---:|
| MATCHED | 2.495 |
| SENSOR_EARLIER_THAN_V49 | 247 |
| SAME_TIME_DIFFERENT_FAMILY | 134 |
| LATER_THAN_V49 | 0 observables por definición prefijo as-of |
| SENSOR_NOT_DETECTED | 0 |
| **Todos los source IDs** | **2.876** |

**Transiciones** en el ledger original: 171 source FVG→sensor Sweep **temprano**, 76 source Sweep→sensor FVG **temprano**, 134 source Sweep→sensor FVG **mismo cierre**. El conteo por par sin dimensión de hora de salida es FVG→FVG 1340, FVG→Sweep 171, Sweep→FVG 210, Sweep→Sweep 1155. **Ninguna dirección H1 opuesta fue instrumentada:** ambos brazos dependen del sesgo V49; no decir que no hay CISD opuesto en el mercado.

### Hallazgo de seguridad epistemológica

El libro de B **sí contiene MFE/MAE y signed_final_price a +15/+30/+60m desde el evento**, que son necesarias para investigación ex post pero **NO observables cuando el Master Frame decide**. Se ha implementado una barrera de datos específica:
 
- `src/qore/infrastructure/trader_lab/capitalizer_a1_cisd_outcome_blind_method_boundary_v1.py` exige schema A2 exacto y la validación física de identidad por `source_opportunity_id` hash original, símbolo, fecha, sesión, H1, M15, familia original y M1 entry close. Cada cambio de esquema B no revisado **FAIL CLOSED como corrupt data**, no veto de trade.
- Se recalcula clase causal **independientemente** desde los tiempos y familias de las dos rutas, incluyendo 247 detecciones anticipadas. Rechaza fuentes cuyo sensor aparece en el futuro, antes de M15 setup, o con delta de minutos contradictorio.
- La **única** salida es el contrato nuevo `A1CISDPredecisionMethodWitness` con campos explícitos (source ID, familia, primera confirmación CISD sensor as-of, cierre original, M15 thesis, dirección heredada, clasificación). Los campos `original_excur` y `sensor_excur` solo se conocen del esquema de entrada y **nunca se leen ni se serializan en el output**. No se remiten `mfe`, `mae`, `risk_geometry_valid`, `signed_final_price`, `uses_ex_post_bars` ni outcome. Ninguna previsión o P&L.
- Aun con prueba física as-of, los campos explícitos `author_eligible_methodology_adjudicated=False`, `enters_master_frame_before_author_review=False`, `changes_trade_admission=False`, `opposite_direction_assessed=False`. La barrera permanece **cuarentenada**: ***no se conecta*** al Master Frame ni se transforma en filtro, hasta adjudicar fuente TTrades y A/B Candle 3.
- Emite `scalper-a1-outcome-blind-cisd-witnesses.jsonl` (todos los source IDs en nine markets) y resumen verificable como artifact de [#38094209281](https://github.com/mezas3238-hue/qore-core/actions/runs/38094209281). Incluso una salida históricamente favorable nunca cambia el orden CISD por política.

### Pruebas científicas y CI

`tests/infrastructure/trader_lab/test_capitalizer_a1_cisd_outcome_blind_method_boundary_v1.py` inyecta un texto-canario **EX_POST_PLUS_60_MIN_WINNER_R_DO_NOT_LEAK_987654321** en ambos `original_excur` y `sensor_excur`; comprueba que el canario y todas las keys de performance jamás aparecen en la salida `asdict` del witness. También prueba: fuente ID, símbolo, sesión, POI/M15 y H1 heredado falsos; evento sensor futuro o antes de tesis; schema no revisado B que agrega PF; `outcome_used_to_admit_trade` falso requerido; denuncia falta de prueba de dirección contraria; y prohíbe marcar la evidencia como validada para entrada.

**Run #38094209281**: Ruff clean, Mypy 2 archivos sin error, **6 pruebas PASS**, 9 artifacts B originales + 9 source V49 y censo 2876 PASS, test real de output libre de MFE/MAE PASS. [Full repository CI #38094209262](https://github.com/mezas3238-hue/qore-core/actions/runs/38094209262): Ruff PASS, **Mypy 1656 archivos sin error, 57 pruebas PASS**. Versionado dentro de branch A1 sin cambio a V49. Cero veto y cero trade modificado. Nada de VPS/LIVE.

### Restricción METHOD FIRST — qué sí y qué no queda desbloqueado

**SÍ:** existe ahora un **formato seguro y auditable para compartir diagnósticos de CISD por source ID**, sin filtrar ganadoras por la información de futuro de B. El enlace al Full Master Frame **aún no ocurre**, deliberadamente.

**NO:** interpretar que 247 sensores tempranos son entradas autorizadas; confiar en la primera secuencia CISD del sensor sin validar POI/swing/HTF; elegir Sweep/FVG por MFE a 30m; usar 381 discrepancias como filtro; afirmar que B haya definido correctamente un C3 para todos los casos; habilitar Full Brain, PF/DD, broker, certificación o LIVE.

**Owner del cierre P0 es B:** 1) fuente primaria literal CISD que identifique serie de velas que realmente produjo el swing/POI y HTF C2/C3, 2) resolver 247 temprano y 134 mismo cierre contra deadlines y precedencia de rutas V49 (delimitación de ventana y tie-breaker), 3) ejecutar A/B diciembre 2025 vs enero 2026 de Candle 3 en las 9 series nativas con source counts, probabilidad favorable a +30m y OOS, sin HARKing. Luego adjudicar cualquier cambio V49, preservar densidad/trades/winner mass y reabrir World Model solo si metodología base certificable.

**Referencia de pérdida sin cambio:** control V49 2.876 source oportunidades, 2.020 trading PAPER, PF 0.66446, DD máximo 236.13R. **PF/DD full historical cognitive nine-market siguen nulos**; nuevas percepciones DEGRADED son integridad de evidencia, NO un edge.
