# VT08 CRT — G-M1 G2/G7, auditores causales R3 (15-OCT-2026)

**Estado:** INVESTIGACIÓN / NO APROBADO / NO CERTIFICADO. No sustituye las siete firmas metodológicas ni los 48 dictámenes humanos G-M2. Revisión por RomeoTPT, SpeculatorFL y TraderFlameseN para inspirar CRT QORE, sin atribuir estas semánticas precisas a los autores. **Sin sizing, órdenes, capital ni datos PnL/OOS**.

## Implementación efectiva

- `src/qore/infrastructure/traders/crt_pure_gm1_g2_g7_causal_audit.py` — auditor de frontera de evidencias, sólo lectura, explícitamente incapaz de conceder ejecución, rearm o capital.
- `tests/infrastructure/traders/test_crt_pure_gm1_g2_g7_causal_audit.py` — positivos y contraejemplos sintéticos; no miden edge ni validan estrategia de autor.
- `.github/workflows/vt08-crt-pure-cognitive-gate.yml` — incluidos en Ruff, mypy y pytest. **Corrección P0 de CI**: la ronda anterior añadía módulo G-M1 external review en Ruff, pero su `pytest` y `mypy` habían quedado fuera de sus comandos; se incluyen ahora y se corrigió la comprobación opcional de timestamp de Owner en el mismo verificador. El CI verde antiguo no probaba esos adversariales; no atribuirle esa cobertura retroactivamente.
- Baseline precedente para comparación: [CI #38799381145](https://github.com/mezas3238-hue/qore-core/actions/runs/38799381145) SUCCESS, **151 passed** (incluyendo G-M1 G2/G7 antes del aislamiento entre mercados). Verificar CI último SHA para todos los nuevos contraejemplos de aislamiento.

## G2 — arbitraje de múltiples referencias

Entradas mínimas: `market`, `parent_id`, `decision_at`, tupla de `CrtGm1Reference` con referencia id, padre, mercado, dirección, reloj de cierre, reloj de descubrimiento, digest SHA256, e indicador **no verificado externamente** de inventario completo.

- Cada referencia debe existir y haberse cerrado/descubierto **antes** de la decisión, pertenecer exactamente al mismo mercado y padre, poseer identidad no duplicada y SHA de evidencia. Referencia futura/diferente mercado/diferente padre/duplicada: excepción fail-closed.
- Sin inventario completo: WAIT, incluso con una sola referencia; cero referencias: WAIT.
- Una y solo una referencia en inventario declarado completo: selección **PROVISIONAL**, nunca trade, ni autoridad. Otras referencias de dirección igual **también** exigen adjudicación: no se elige con PnL, cercanía, ranking oculto ni ventaja histórica.
- Dos o más referencias: ABSTAIN y motivo `MULTIPLE_REFERENCE_PRIORITY_NOT_ADJUDICATED`, aunque ambas indiquen la misma dirección; la jerarquía old CRTH aún no está aprobada y no debe fingirse.

**Limitación fuerte:** este módulo no construye ni autentica exhaustividad de inventario PIT desde velas H4; recibe un inventario a auditar. No equivale a cerrar G2 de forma operativa. Su valor es impedir elegir retrospectivamente referencias en el borde de decisión, hasta que la definición de inventario/selección sea revisada por auditor.

## G7 — ciclo, conflicto y rearm

Entradas: evento propuesto con `market`, `parent_id`, `source_event_id`, `hypothesis_id`, `event_generation`, `observed_at`, `decision_at`, y ledger previo de eventos del **mismo mercado**.

- Historias con otro mercado, duplicación de padre/source/hypothesis, futuro respecto de la decisión o generations/timestamps no monótonos: excepción fail closed.
- Primer evento causal: PROVISIONAL, sin permiso de entrada.
- Cualquier segundo intento en el **mismo H4 padre**: ABSTAIN (`H4_PARENT_ALREADY_USED`), aunque cambie fuente/hipótesis/generación. Invalidez previa **no** habilita un segundo intento sobre el mismo padre.
- Reutilizar fuente o hipótesis histórica en otro padre: ABSTAIN. Generación estancada o anterior: ABSTAIN. Nuevo source observado antes de decidir el evento anterior: ABSTAIN.
- Sólo padre distinto, fuente e hipótesis distintas, generación mayor y reloj posterior **Y todas las hipótesis previas con terminación observada causalmente antes de la nueva fuente** pueden recibir PROVISIONAL (`NEW_PARENT_AND_SOURCE_CAUSALLY_OBSERVED`); sin testigo de terminal anterior se responde WAIT (`PRIOR_THESIS_NOT_TERMINAL_BEFORE_NEW_SOURCE`); un terminal del futuro provoca rechazo. El resultado nunca concede `grants_rearm_authority` ni ejecución o capital.
- No usa resultados de la operación anterior, wick-hit posterior, OOS, costes o PnL.

**Limitación fuerte:** el ledger es un *input*, no un estado con custodia independiente. Sin prueba de integridad/secuencialidad del histórico completo, cualquier evento ausente permitiría clasificar "primero" artificialmente. G7 requiere enlazar source H4 canónica con estado cognitivo/ledger persistido y verificación independiente; la auditoría actual no firma G-M4.

## Tests adversariales y criterios de revisión metodológica

Casos obligatorios: bull/bear contradictorios y referencias con igual dirección; fuentes duplicadas, datos futuros, ausencia de referencia, inventario incompleto, digest inválido, referencias cruzadas por mercado o padre, "mejor ganador a posteriori"; rearm mismo padre con distinta ID, mismo source/hypothesis nuevo padre, generación atrasada, evidencia tardía/vieja, historiales duplicados/futuros, contaminación AUDUSD/USDJPY, terminal previo ausente, terminal conocido solo después de nueva fuente y terminal futuro. Sin mock de aprobación Owner ni de revisor para declarar PASS.

## No regresiones permitidas

V1=54 candidatos conceptuales, V2=745 y trayectoria desfavorable, V3=139 y trayectoria desfavorable; son identidades **congeladas**. Estos auditores son módulos nuevos de investigación, **no** modificaciones retrospectivas de los tres generadores ni un V4 preregistrado. La evidencia de geometría adversa V2/V3 persiste.

## Trabajo verdaderamente pendiente

1. Validar una política inventariable causal para G2 y observar casos reales de niveles competidores desde H4 source, dejando separados fuente original y propuesta QORE. No deducirla del resultado futuro.
2. Integrar G7 en un ledger inmutable/auditado con generación y parent de mercado, y reproducir eventos reales incluidas invalidaciones y 5 UNKNOWN sin inventar terminal.
3. Obtener revisor y Owner distintos y autenticados para artículo por artículo (issue #976). `G-M1 G2/G7 auditor verde` **no es** `G-M1 PASS`.
4. Cerrar G-M2 blind independiente; G-M3 metacognición contrastada con verdad externa; G-M4 evidencia y custodia; G-M5 sólo con los cuatro PASS auténticos.
5. Global económico separado: contrato de entrada ejecutable BID/ASK, OOS nuevo no visto, PF/Sharpe/Sortino, DD patrimonial exclusivamente CIBO/Risk, WFO/Monte Carlo y stress; no sizing dentro de VT08. Proteger Atlas antes del vencimiento #837.

**Estados:** G-M1..G-M4 PARTIAL, G-M5 NOT ISSUED, GLOBAL NOT CERTIFIED, SIN MERGE, SIN DEMO/LIVE/ÓRDENES/VPS/SIZING.

**Nota sobre autoridad de cierre:** `terminal_observed_at` de cada registro sigue siendo un claim del ledger, no una firma del proveedor ni comprobación independiente de G-M4. G7 permanece PARCIAL hasta enlazar esos campos con evidencia M5 temporal, fuente y custodia auditada. No aumentar contador PASS por este código.
