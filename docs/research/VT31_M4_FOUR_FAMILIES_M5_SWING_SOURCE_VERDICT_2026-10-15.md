# VT31 M4/M5 — VEREDICTO SEMÁNTICO DE FUENTES, COGNITIVA Y FAMILIAS
**15-OCT-2026.** Mandato Owner: certificar método + cognitiva, **NO evaluar PF/DD/Sharpe/Sortino/lotaje**. PR #958 DRAFT child #954; no merge/live/DEMO/VPS/FundedNext.

## Evidencia ejecutada — no certificado automático
- [CI SUCCESS #38710774260](https://github.com/mezas3238-hue/qore-core/actions/runs/38710774260), código ensayado `b0adbeddefc2717fbb150f9502241aa44cf467fd`, **79/79 tests PASS** + Ruff PASS. Histórico NAS100 M1 original **1.059.784 M1**, SHA256 `0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa` verificado (desarrollo previo visto, no fresh OOS).
- [Artifact de prueba y decisiones #11960700796](https://github.com/mezas3238-hue/qore-core/actions/runs/38710774260/artifacts/11960700796), ZIP SHA256 `9ae5fac3ea01d07405d4d571d587b5e3f450e3d150fba77b39cfb7c6dad31804`.
- [Prerregistro anterior al código](https://github.com/mezas3238-hue/qore-core/blob/67c35f7bf9284cb1feeee9bd54261abec21a6c9f/docs/research/VT31_M4_FAMILY_SOURCE_PREREG_2026-10-15.md). El testigo #958 es **solo diagnóstico**: consume el COG V2 read-only y la estructura FVG 3 M1 QORE previamente existente, sin construir `CognitiveDecision`, sin crear entradas, stops numéricos ni fills.

## La fuente del autor realmente dice
- [TTrades The AM Silver Bullet Strategy on NQ — 19-JUN-2025](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/): después de H1 09→10 NY y primer barrido, dirección inversa con objetivo opuesto, requiere **confirmación** y menciona displacement back into range, Fair Value Gap en estructura, Order Block y Breaker Block; indica stop más allá del swing high/low que originó desplazamiento.
- [PDF fuente original 6 páginas](https://ttrades.com/wp-content/uploads/2026/01/Silver_Bullet_AM_Session_TTrades_PDF.pdf): figuras de horario y framework, **no definición algorítmica M1 única** de detección OB/Breaker, jerarquía entre las cuatro familias, pivot3×1.25 body, regla de stop C2, espera exacta del regreso ni política de eventos simultáneos. No extraer autoría de la ingeniería QORE.
- Las dos fuentes no autorizan asignar mayor prioridad al primer FVG que a OB/Breaker por estadística; la selección exige fuente adicional o versión **QORE propia declarada**, con nueva revisión, antes de certificar fidelidad al autor.

## Auditoría sobre decisiones contextuales históricas — NO operaciones
Población congelada: 483 días de primera vuelta sin proxy MSS en la misma M1, ya estudiados en #949/#952/#954. Protocolo: a cada nuevo cierre M1, V2 conserva primer barrido/retorno y no emite trades; el testigo `confirmed_m1_fvg` revisa **solo 3 M1 contiguas dentro de la ventana NY 10–11**, después del regreso, alineación direccional y antes de invalidación/consumo observado del objetivo. El FVG es **QORE geometric**, no una prueba del setup autoral.

| Caso M4 observado en los prefijos | Contextos | Lectura correcta |
| --- | ---: | --- |
| **Geometría QORE de 3-M1 FVG** observada en contexto fuente previo a invalidez | **457** | No prueba desplazamiento, estructura interna requerida por el autor, OB, Breaker, prioridad o validez de una entrada |
| No se observó esa geometría elegible en contexto | **26** | No implica que el autor careciese de oportunidad mediante otra familia |
| **Total** | **483** | Fuente de investigación ya vista, NO trades |
| Contextos cuyo estado V2 termina INVALIDATED por raid contrario | **48** | Superpuestos con categorías de FVG; invalidez posterior debe revocar, no mantener intent |
  
Primer día fuente del archivo: 02-OCT-2023 (FVG geométrico); primer día sin esa geometría bajo contrato: 31-ENE-2024. Exactos timestamp/casos por día en artifact. **Los 457 no son 457 entradas TTrades correctas**; números solo prueban que el testigo observa formas y reconoce límites de sus afirmaciones.

## Matriz de certificación semántica M4–M6
| Gate | Estado | Por qué |
| --- | --- | --- |
| M4 DISPLACEMENT | **AUTHOR_CONCEPT_UNDERDETERMINED_M1_TRIGGER** | Autor exige confirmación desplazamiento pero no entrega umbral calculable universal por M1 |
| M4 FVG | **QORE_GEOMETRY_OBSERVED_NOT_AUTHOR_CERTIFIED** | La forma de 3 M1 por sí sola no prueba ubicación estructural/confirmación/selección |
| M4 ORDER BLOCK | **NOT_IMPLEMENTED_AUTHOR_RULE_UNDERDETERMINED** | No inventar “última vela opuesta” como autoría exacta sin adjudicación |
| M4 BREAKER BLOCK | **NOT_IMPLEMENTED_AUTHOR_RULE_UNDERDETERMINED** | No inventar quiebre/retest de swing con geometría distinta sin fuente |
| M4 concurrencia/prioridad | **AUTHOR_AMBIGUITY** | Carecemos de orden fuente inequívoco cuando varias familias coinciden |
| M5 stop swing causante | **NOT_ATTESTED** | El artículo define relación causal swing→desplazamiento, NO “siempre extremo de sweep” o C2+tick; no hay witness independiente con timestamp/causa |
| M6 firmas independientes | **PENDING** ([issue #897](https://github.com/mezas3238-hue/qore-core/issues/897)) | No falsificar roles COG/OPS desde una sola cuenta |

**Resultado correcto:** testigo M4 implementado/CI verde; **CERTIFICACIÓN M4/M5 NO OTORGADA**, hasta fuente autoral más específica o ratificación explícita de política QORE diferenciada y testigos negativos. El COG V2 de espera permanece **read-only y no habilitado para trading**.

## Próximo trabajo P0 para salir del bloqueo
1. M4 resolver **por doctrina** 4 familias, con vídeo del autor y ejemplos etiquetados manualmente, circunstancias donde el COG debe WAIT/REJECT y reglas de concurrencia; si no hay regla pública, `AUTHOR_AMBIGUITY` y propuesta QORE separada, nunca llamada author-perfect.
2. M5 modelar **swing causante** como evidencia M1 con `pivot_confirmed_at < displacement_at <= cog_asof`; además detectar varios swings igualmente plausibles y emitir `UNKNOWN` antes de inventar stop. La regla de cuánto buffer requiere fuente/version separado.
3. M6 dos atestaciones con identidades independientes sobre SHA exactos del contrato (G3 #896) y luego sobre M4/M5 por perfil. En GitHub la issue #897 sigue OPEN; no certificación completa sin ese control.
4. Mantener Trader Lab L1–L10 y economía en expediente diferente sin condicionar Gate de método/COG al resultado de PnL.

**NO MERGE, NO LIVE, NO sizing VT31, NO mejora cuantitativa disfrazada de certificación.**
