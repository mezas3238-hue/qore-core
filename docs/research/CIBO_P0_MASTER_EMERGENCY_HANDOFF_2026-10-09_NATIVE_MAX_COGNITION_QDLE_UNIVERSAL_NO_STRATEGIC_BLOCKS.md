# ACTUALIZACIÓN CANÓNICA MÁS RECIENTE (2026-10-09, TRADER LAB REAL)

> **PRÓXIMO ARQUITECTO: leer primero** [HANDOFF MAESTRO P0 3368 COGNITIVA + QDLE](CIBO_MASTER_P0_HANDOFF_2026-10-09_TRADER_LAB_3368_FULL_COGNITION_QDLE_REPAIR.md). La auditoría nueva [Trader Lab #37949977967](https://github.com/mezas3238-hue/qore-core/actions/runs/37949977967) pasó la ejecución PAPER con Market Atlas: 3368 señales, 20 descartadas por geometría antes de QDLE, 2809 sin lote, 539 PAPER abiertas, 537 cerradas, 2 abiertas; P&L neto PAPER −$50.78, PF .7167, DD **CASH** 85.20%, caja ~$9.08, DD real de equity sin certificar. CIBO reusa política rígida y 4 cap reciclados, QDLE DB efímera por señal; **P0 NO RESUELTO**. Este handoff antiguo tiene hallazgos históricos válidos, pero cifras y ejecutores anteriores NO sustituyen el nuevo master. QDLE Stellar Instant corregido, NO legacy.

---

# QORE CORE — HANDOFF MAESTRO DE EMERGENCIA P0
## Integración REAL de la cognitiva CIBO MAX Native + gestión activa universal de las 3.368 señales + cuatro motores económicos + QDLE

**FECHA:** 2026-10-09  
**ESTADO:** CRÍTICO / INTEGRACIÓN NO RESUELTA / PROHIBIDO DECLARAR CIBO CERTIFICADO O LIVE READY  
**REPOSITORIO:** `mezas3238-hue/qore-core`  
**RAMA CANÓNICA:** `agent/cibo-sovereign-integration-p0-20261008`  
**HEAD VERIFICADO ANTES DE REDACTAR:** `30845aa5133ce2d76f2f092298252f7c9ead8696` (continuar desde el HEAD más nuevo antes de modificar)  
**PR COORDINADOR:** [#745 — DRAFT, NO LIVE](https://github.com/mezas3238-hue/qore-core/pull/745)  
**DUEÑO DE LA SIGUIENTE ITERACIÓN:** siguiente arquitecto integrador P0: cerebro CIBO MAX Native → decisiones ejecutables → QDLE → administración de posición → settlements → tesorería.

> **ALERTA CEO / INSTRUCCIÓN NO NEGOCIABLE DE PRODUCTO:** **NINGÚN FILTRO ESTRATÉGICO O COGNITIVO PUEDE VOLVER A DESCARTAR UNA SEÑAL DE CORE.** Todas las 3.368 entradas deben llegar al cerebro CIBO, ser razonadas y obtener un plan de administración. CIBO NO ES UN GATE DE ADMISIÓN. CIBO ADMINISTRA LA ENTRADA, EXPOSICIÓN, CAPITAL, SL, PARCIALES, TRAILING, BREAK-EVEN Y SALIDA. QDLE ES EL ÚNICO CALCULADOR FÍSICO DE LOTES. Retirar y aislar restricciones artificiales de Sizing, CIBO Compuesto, Adaptive Leverage, Portafolio Compuesto y filtros MAX que impidan estudiar la capacidad universal de CIBO en PAPER. Los límites de solvencia/riesgo real, posiciones, comisiones, margen, lot grid, broker/proveedor y autenticación **NO** son filtros estratégicos: son restricciones físicas inevitables y no se deben eliminar en LIVE.

---

# 0. LECTURA INMEDIATA — QUÉ ESTÁ ROTO

**GRAVEDAD P0:** CIBO MAX Native **sí ejecuta o provee evidencia de su cognitiva**, pero en el replay completo sus conclusiones **NO gobiernan realmente ninguna ejecución económica ni salida**.

1. La cognitiva MAX aporta miles de recibos; el adaptador `scripts/cibo_p0_native_max_manager_advisory_3368.py::classify_native_advisory` hace una **traducción estática** de antiguas disposiciones de selección:
   - `COGNITIVE_BLOCK → BANK` para **1.804** señales.
   - `CAPITAL_BLOCK → MEDIUM` para **1.553**.
   - `RISK_REVIEW_READY → ATTACK` para **11**.
   Esta clasificación es una hipótesis nueva en modo SHADOW. **No es CIBO razonando los parámetros de administración concretos de cada operación** y no debe ser confundida con una elección nativa real de modo.
2. El programa `scripts/qdle_3368_dual_ledger_replay.py` recibe `--native-max-management-advisories`, copia digest/calibración/mode a `event` y fija **`cibo_max_native_exit_policy_executed = False`**. Después llama al calculador `propose_received_trader_management` con NAV, SL, fee y fuente **sin que el razonamiento Native MAX determine los parámetros usados**.
3. Al modificar el SL económico, QDLE genera una `ECONOMIC_STOP_QDLE_PHYSICAL_QUOTE_SHADOW`, **NO una operación liquidada ni una posición con administración**. El replay no tiene barras/ticks ejecutables bid/ask para reconstruir el recorrido.
4. El subconjunto que sí se liquida usa **`gross_structural_outcome_r` del Trader** y el SL estructural antiguo. **No consume salidas de CIBO** y es matemáticamente incorrecto usar ese R para operaciones cuyo SL/gestión cambió.
5. `src/qore/infrastructure/cibo_compound_capital.py::propose_p0_compound_vote` calcula rachas de pérdidas de `reconciled_cashflows`; en el replay éstos se fabrican **como cashbook de control** desde `recent_settlements[-3:]` y `REPLAY_SETTLED` en `scripts/qdle_3368_dual_ledger_replay.py`. La regla `THREE_SETTLED_LOSSES_HAIR_CUT` reduce presupuesto del **5% al 2,5% del NAV** después de tres pérdidas del Trader sin gestión CIBO, y produjo **2.782** no financiables. **Error de procedencia del experimento, no necesariamente bug aritmético del motor.**
6. El replay da sensación de `3368/3368` administradas, pero prueba solamente **3368/3368 recibidas/anotadas/cotizadas**. No prueba `3368/3368` gestionadas con cognitiva real.

**PROHIBICIÓN DE CIERRE FALSO:** No repetir «CIBO MAX Native integrado y funcionando» por el hecho de que `native_max_3368_cognitive_evidence_joined=True`. El siguiente arquitecto debe demostrar **efecto causal** de cada decisión cognitiva en el plan y en la evolución de posiciones. Sin eso, el P0 sigue ABIERTO.

# 1. ORDEN DEL CEO — DEFINICIÓN PRÁCTICA DE «CORE SIN BLOQUEOS»

**Separar expresamente:**

- **ADMISIÓN AL CEREBRO:** **3368/3368 ALWAYS ACCEPTED**. Ningún `COGNITIVE_BLOCK`, `CAPITAL_BLOCK`, predicción negativa, low confidence, riesgo discrecional de módulo ni research certification puede ocultar o eliminar la entrada original del Trader. Toda señal conserva fingerprint/Trader/decisión/SL estructural/TP y siempre obtiene `CIBO_MANAGEMENT_RECEIVED` y un plan o recibo explícito de administración pendiente. No filtrar por beneficio esperado para reducir artificialmente el denominador.
- **ADMINISTRACIÓN:** CIBO MAX Native debe emplear capacidad cognitiva real para elegir política de riesgo, modo BANK/MEDIUM/ATTACK (o equivalente fundamentado), SL protector viable, cuándo tomar parciales, trailing, BE, defensa y cierre. Las salidas deben poder redirigirse por evolución de mercado sin lookahead.
- **ASIGNACIÓN:** Los cuatro motores aportan **información económica** y coordinación; no deben crear un segundo veto artificial de Core. Investigar y eliminar/topar en un brazo PAPER las políticas discrecionales que no respeten el nuevo paradigma. Ningún motor puede mandar lotes ficticios ni convertirse en autoridad de envío.
- **QDLE:** calcular único volumen físico por señal sobre riesgo **máximo dinámico 5% del QORE NAV propio** (inicial USD60; 5% = USD3 iniciales), **SL + comisión de apertura + comisión de cierre + buffers/slippage**, comisiones reservadas y apertura debitada en su instante, margen/broker/dirección/límites de concentración comprobados. QDLE no es una segunda cognitiva de selección. Si no cabe el lote mínimo legal, debe explicar la imposibilidad física, solicitar a CIBO alternativa viable (SL protector permitido, menos exposición/espera técnica o instrumento adecuado) y mantener la señal **contabilizada**, no hacer `silent drop`.
- **PROHIBICIÓN DE VIOLAR MATEMÁTICAS:** «Sin bloqueos de Core» **no** significa forzar `0.01` cuando el SL + fees supera 5%, inventar sub-`0.01` lots, ejecutar sin fondos, ignorar broker stop-level/margen, saltarse regla real del proveedor o emitir órdenes LIVE sin autorización. Imposibilidad física debe ser `MANAGEMENT_RECEIVED_QDLE_PHYSICALLY_UNEXECUTABLE(reason)`, no `CIBO_REJECTED_SIGNAL`.

**El experimento PAPER puede omitir todos los topes estratégicos, nunca los invariantes duros.** El modo de riesgo en producción NO se modifica hasta validar la economía y confirmar especificaciones MT5.

# 2. ESTADO REAL DE GITHUB Y BASE DE CONTINUIDAD

- Repo `mezas3238-hue/qore-core`.
- Branch `agent/cibo-sovereign-integration-p0-20261008`.
- PR [#745](https://github.com/mezas3238-hue/qore-core/pull/745) **DRAFT**, base `agent/cibo-architect-3-qdle-mt5-physical-20261008`.
- HEAD visto al preparar este handoff: `30845aa5133ce2d76f2f092298252f7c9ead8696`. Al iniciar, volver a leer HEAD y revisar archivos de otros arquitectos; NO hacer reset ni checkout de ref antiguo, no pisar trabajo ajeno.
- Handoff antecedente: `docs/research/CIBO_SOVEREIGN_INTEGRATOR_P0_CONTINUITY_2026-10-08.md`.
- Director de estados y plan shadow: `src/qore/infrastructure/cibo_sovereign_integration.py`. **No es autoridad live** y advierte que aún necesita instrucciones CIBO y broker probados.
- Cerebro nativo rico: `src/qore/infrastructure/cibo_native_max_cognitive_episode.py`; runner autónomo `scripts/cibo_single_account_historical_ceiling_replay.py`.
- Adaptador erróneo MAX→modos estáticos: `scripts/cibo_p0_native_max_manager_advisory_3368.py`.
- Motor de replay a integrar: `scripts/qdle_3368_dual_ledger_replay.py`.
- Contrato entrada universal + SL: `src/qore/infrastructure/cibo_trader_signal_administration.py`.
- Motor de salidas conservador, TODAVÍA desconectado del replay financiero: `src/qore/infrastructure/cibo_managed_exit_replay.py`.
- Motor físico universal de lote/ledger: `src/qore/infrastructure/qore_dynamic_lot_engine.py` y adaptador `src/qore/infrastructure/qdle_mt5_read_only.py`.
- Integración 4 motores: `src/qore/infrastructure/cibo_four_motor_policy.py`, `src/qore/infrastructure/cibo_four_motor_qdle_proposal.py`, `src/qore/infrastructure/cibo_account_sizing_authority.py`, `src/qore/infrastructure/cibo_compound_capital.py`, `src/qore/infrastructure/cibo_marginal_leverage_utility.py`, `src/qore/infrastructure/cibo_core_compound_portfolio.py`, `src/qore/infrastructure/qdle_cibo_authority.py`.
- Workflows relevantes:
  - `.github/workflows/cibo-p0-native-max-manager-qdle-3368.yml`.
  - `.github/workflows/cibo-p0-3368-paper-no-strategy-caps.yml`.
  - `.github/workflows/cibo-p0-manager-qdle-replay.yml`.
  - `.github/workflows/cibo-p0-compound-3368-root-cause-audit.yml`.
  - `.github/workflows/cibo-ceo-experimental-3368-integration-replay.yml` **LEGADO**: conecta aprobaciones cognitivas en modo GATE 11/3368; no repetir como arquitectura final.

# 3. FUENTES SELLADAS Y REPRODUCIBILIDAD

**Fuente Trader 2019–2022**: 3368 oportunidades originales, GitHub artifact `11451743578`; ZIP SHA256 **`d439957f21e2f79148b5a2fb75a53db6fa448698f17aeb6978f379ed3547f7ea`**; miembro `walk-forward-manifest.json`. Id único `signal_fingerprint`; `market_decision_at`, `settlement_outcome_research_only.entry_at/exit_at/gross_structural_outcome_r`, `trader_opportunity`.

**MAX Native genuino, evaluación predecisión histórica**: artifact `11588089131`; ZIP SHA256 **`eebf6de43da63aadc200a3783109246188d46e0fcdd7da127f07eff815d6cec6`**; miembro `cibo-native-baseline.json`. `decision_receipts` contiene 3368 fingerprints/digest/semánticas y evidencia de cognición con `native_maximum_intelligence`, `full_semantics_consumed`, `outcome_used_for_predecision=False`.

**Re-evaluación fresca de MAX Native**: workflow [#37912035662](https://github.com/mezas3238-hue/qore-core/actions/runs/37912035662), commit de workflow `057707e687db8030d2a191a4d70fbb56130d1b0b`. **EN CURSO al verificarse esta actualización:** estaba ejecutando `Recompute FRESH actual Native MAX engine for the full 3368 original signal timeline`. **PRIMERA ACCIÓN DEL SIGUIENTE ARQUITECTO**: leer status/job logs/artifact final; si falla corregir y repetir, si termina correctamente fijar artifact y comparar cada digest con el basal. NO declarar éxito retroactivamente. El run exitoso [#37911594114](https://github.com/mezas3238-hue/qore-core/actions/runs/37911594114) consumió recibos MAX sellados **previos**, NO una recomputación fresca.

**No hay en el manifiesto sellado la trayectoria completa bid/ask intratrade por cada señal**, requisito imprescindible para SL económico/trailing/parcial/BE/adversa. No inventar 3368 cierres gestionados ni mezclar datos posteriores a `market_decision_at`.

# 4. RESULTADOS CONGELADOS — NO VOLVER AL REPLAY DE 11

### 4.1 Replay CONTROL QDLE físico simulado con SL y cierres originales

[Actions #37904592323 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37904592323), artifact `11603757283`, 3368 señales, **359** QDLE financiables originales, **3009** no financiables, $60→**$9.51746750**, PF proxy **0.78147160**, DD sobre NAV CERRADO **87.40357309%**, fees apertura **$54.07647168** + cierre **$54.07647168**. **Estos resultados NO son de CIBO gestor, corresponden al CONTROL con Trader structural R**.

### 4.2 CIBO propuso SL económico + QDLE con topes de 4 motores

[Actions #37907644177 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37907644177); artifact `11605550958`. 3368 CIBO recibidas; 813 SL originales conservados, **2555** SL económicos propuestos desde NAV dinámico del CONTROL, **359** QDLE financiables SL original, **209** quotes QDLE con SL económico nuevo, **2800** no financiables, **0** fills MT5. De 2800, **2782 `CIBO_COMPOUND`**, 17 Bank, 1 capacidad. Las 209 NO están en el PnL del control.

### 4.3 Causa exacta de 2782 límites CIBO Compuesto

[Actions #37909235818 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37909235818), artifact `11605372636`; informe `docs/research/CIBO_P0_COMPOUND_2782_ROOT_CAUSE_2026-10-09.md`. Los **2782/2782** provienen de `THREE_SETTLED_LOSSES_HAIR_CUT`, `cap=0.5 × 5% NAV`. 2337 de ellas tenían SL económico nuevo y 445 conservaban SL. **Cashflows falsamente adecuados para el objetivo manager**: pérdidas desde **salidas Trader del CONTROL**, no pérdidas de gestión CIBO. En este escenario `protected_capital=0`, `floating_loss_reserve=0`; ninguna reserva 70% explica el bloqueo.

### 4.4 Ablación PAPER de CUATRO TOPES ESTRATÉGICOS

[Actions #37910444519 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37910444519), artifact `11606054452`, informe `docs/research/CIBO_P0_3368_PAPER_NO_STRATEGY_CAPS_2026-10-09.md`. `--experimental-cibo-administrator --experimental-paper-bypass-strategy-caps`: **3368/3368** cotizaciones, **430** con SL original + **2938** con nuevo SL económico; **0** no financiables *en los supuestos proxy optimistas*; **0** MT5 fills; métricas CIBO auténticas `NULL`.

**Muy importante:** las **430** posiciones SL original solamente, con Trader R previo, originaron **$60→$6.67428534**, closed-equity DD **93.19891524%**, PF proxy **0.77336808**. No atribuir al CIBO de las 2938 nuevas, que no se liquidaron ni entraron al NAV verdadero.

### 4.5 MAX Native cognitiva conectada en modalidad anotación (NO control efectivo)

[Actions #37911594114 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37911594114); artifact `11606736959`; informe `docs/research/CIBO_P0_NATIVE_MAX_MANAGER_QDLE_3368_RESULTS_2026-10-09.md`:
- Cognitiva MAX con 3368 recibos verificados, sin `admission gate`.
- **1804** BANK shadow (antes `COGNITIVE_BLOCK`); **1553** MEDIUM shadow (antes `CAPITAL_BLOCK`); **11** ATTACK shadow (antes `RISK_REVIEW_READY`).
- **Con topes** exactamente **359 SL original + 209 nuevo SL QDLE quote + 2800 sin lote**.
- **PAPER sin topes** exactamente **430 SL original + 2938 nuevo SL QDLE quote + 0 sin lote**.
- **MAX cognitiva no alteró lote ni salida**: las cuentas coinciden exactamente con replay anterior sin la cognitiva, porque sólo se anotaron recibos y modos estáticos.
- No se ha demostrado CAPITAL/PF/DD de CIBO MAX administrador en ninguna de las 3368.

**Interpretación definitiva:** nuevo cuello de botella P0 no es ya «eliminar el selector»; es **cablear realmente el razonamiento cognitivo a decisiones económicas con efecto causal y conectar esas decisiones a salidas de precios**. No repetir experimentos que sólo agreguen un campo `native_digest`.

# 5. RIESGO DE SEGURIDAD + FUENTE FINANCIERA: VERDAD SEPARADA

- **Capital económico QORE:** USD60 inicial, riesgo por entrada `5% × NAV QORE dinámico`; no usar USD2000 de MT5 como NAV para sizing.
- **Capital broker de margen MT5:** escenarios existentes simulan USD2000; no asumir que USD2000 son fondos reinvertibles de Core. Los datos actuales de margin/símbolos/fee dependen de pantallazos de FundedNext 2026, no de fichas históricas autenticadas.
- **Instrumentos:** AUDJPY, EURUSD, GBPJPY, GBPUSD, NAS100/NDX100, XAUUSD. Resolver alias real via MT5 y evitar la equivocación índice NAS100 vs NDX100/USTEC.
- **Comisión forex proxy** USD14 por lote round trip (USD7 apertura y USD7 cierre). NDX USD20/lot RT sensibilidad, no fee broker demostrada; oro fee nominal proxy. Descontar comisión apertura **al abrir**, cierre **al liquidar**, reservar ambos al riesgo por SL. FXJPY convertir correctamente a USD.
- **Grid broker**: 0.01 lote mínimo asumido para los seis símbolos hasta que MT5 lo confirme por ficha; tick size, stop level, lot step, congelación, ejecución y orden son diferentes por símbolo.
- **Prov risk**: el replay usa `--provider-trailing-usd disabled` = **límites FundedNext NO COMPROBADOS**; nunca interpretarlo como ausencia de límites en cuenta real.
- **Stop económico**: sólo si respeta precio actual, dirección, min broker stop distance, estructura y all-in SL+fees+buffers <= 5%. Estrechar stop no garantiza menor pérdida observada ni beneficio: puede disparar antes por volatilidad, spread y gaps.
- **Gaps/slippage/spread**: las pérdidas reales pueden sobrepasar el SL en discontinuidades; 5% es presupuesto de planificación, no garantía absoluta del fill.
- **No cambio LIVE**: el bypass `--experimental-paper-bypass-strategy-caps` sólo actúa en script de research; las políticas de seguridad reales siguen intactas.
- **No operador fantasma**: cotización QDLE ≠ `order_check` real ≠ `order_send` real ≠ fill MT5 ≠ settlement CIBO. Siempre mostrar cada conteo por separado.

# 6. MISIÓN PRINCIPAL P0 — CONECTAR CEREBRO MAX NATIVE A ADMINISTRACIÓN REAL

**No comenzar ajustando los porcentajes de hair-cut ni inventando nuevas tablas de multiplicadores.** Cambiar primero la arquitectura del flujo.

Implementar, documentar y probar una interfaz específica entre:

`TRADER SIGNAL -> CIBO MAX NATIVE TRUE COGNITIVE EPISODE -> EXPLICIT MANAGEMENT DECISION -> 4 ECONOMIC ENGINES -> QDLE PHYSICAL QUOTE -> POSITION PATH MANAGER -> REALISTIC ECONOMIC SETTLEMENT -> CIBO CASHBOOK+COMPOUND -> NEXT SIGNAL`.

**Obligatoria una decisión estructurada, tipada e inmutable por señal**, no un mapper `COGNITIVE_BLOCK→BANK`. Ejemplo de campos de contrato:

```
CiboCognitiveManagementDecision {
  signal_fingerprint, trader_id, decision_at, native_episode_digest,
  input_data_provenance, reasoning_context_digest, risk_assessment,
  market_regime, market_scenarios, expected_net_utility,
  confidence_calibration, chosen_management_mode, mode_evidence,
  economic_stop_proposal, trade_risk_usd_proposal,
  partial_take_profit_plan, trailing_plan, breakeven_trigger,
  defensive_exit_conditions, full_close_conditions,
  dynamic_revision_policy, cognitive_reason_codes,
  no_future_data_consumed, research_or_live_scope
}
```

- No elegir decisiones sólo a partir de `capital_disposition` legado. Inspeccionar la semántica rica de `CiboNativeMaxCognitiveEpisode` (facultades, percepciones, incertidumbre, escenarios, causalidad, consulta CF01–CF19, metacognición), y convertirla en acciones sustentadas **por datos disponibles en el instante**.
- Crear un `CiboPositionManagementDecision` por cada nuevo evento de mercado/posición: cerrar parcial, BE, actualizar SL, trailing, gestión negativa, cerrar completo, gestionar margen/fees; causal, justificable y trazable.
- El estado CIBO no puede limitarse a `native_max_cognition_read=True`, `manager_mode_SHADOW_from_native_legacy_disposition` y `exit_policy_executed=False`. Se requiere una prueba de que `cognitive_management_decision` **altera una acción económica concreta** y deja auditables entrada/stop/lote/tiempo/pérdidas sin confundir research con broker.
- Si confianza/semántica incompleta: **la señal NO desaparece**. Generar resultado conservador `NEEDS_EVIDENCE_OR_BROKER_REQUOTE`; si el modo es PAPER, registrar recomendación provisional; si es LIVE, no inventar órdenes ni saltar seguridad broker.
- La cognitiva debe revisar la posición durante su vida, no sólo al aceptar entrada. No sólo consumir una vez el recibo Native MAX de predecisión.

# 7. CUATRO MOTORES + QDLE UNIVERSALES, SIN GATES ESTRATÉGICOS

**Sizing:** riesgo 5% NAV dinámico como marco, stop adverse USD/lote + comisiones apertura+cierre + conversiones + slippage, broker grid. Que aporte una valoración, no `REJECT` de la señal.

**CIBO Compuesto:** su fuente debe ser **únicamente closed realized settlements gestionados por CIBO** con ticket/época/operación y fees. Jamás recibir `REPLAY_SETTLED` del control como historial de pérdidas del manager. Mantener `THREE_SETTLED_LOSSES_HAIR_CUT` como política de protección estudiable y opcional en PAPER, pero **no dejarla castigar operaciones por pérdidas ajenas**. Diseñar ciclo de vida de reducción y recuperación basado en settlements auténticos, con experimentos preregistrados y sin bloqueo indefinido por falta de lotes mínimos. Separar reservas protegidas/working capital/reinversión y devolver causa completa por decisión.

**Adaptive Leverage:** vigilar margen MT5, exposición y concentración, permitiendo apalancamiento viable. Su recomendación no es multiplicador abstracto `10000x` convertido a lote ficticio; volumen se determina con contrato broker real.

**Portafolio Compuesto:** mantener Bank/Cushion/compounding/transferencias con identificador de fuente y efecto en NAV, evitar double spend de capital, exposiciones correlacionadas y netting. No usar cuenta broker nominal como patrimonio económico QORE.

**QDLE único servicio físico:** `QDLEIntent` recibe cuatro evaluaciones + instrucción CIBO con referencias verificables al mismo account_epoch; calcula volúmenes concretos y recalcula tras entrada/settlement (riesgo stop + fees, vol step, margin, capital, source). No permite `0.01` ilegal ni un riesgo >5%; jamás sustituir acción CIBO por aprobación cognitiva de mercado.

**Sin bloqueos estratégicos no implica sin defensa contra insolvencia:** en el replay crear `ALL_TRADER_SIGNALS_ADMINISTERED` y estado por cada uno `ECONOMIC_PLAN_READY` o `BROKER_PHYSICAL_CONSTRAINT_PENDING`, todos contabilizados, sin nueva tabla de `CIBO_ADMISSION_BLOCKS`.

# 8. REPARAR EL BUCLE DE TRES PÉRDIDAS

**Error exacto del escenario:** el closure histórico de Trader sin CIBO administra la racha de CIBO Compuesto. Resulta 2782 recortes al 2.5% NAV y una espiral de bajo capital.

**Regla de alimentación no negociable:** observaciones de `reconciled_cashflows` usadas para racha en el brazo `manager` **sólo desde `CIBO_MANAGED_SETTLED`**, nunca `TRADER_CONTROL_SETTLED`. En cualquier proceso:
1. Etiquetar proveniencia de cada cashflow: `TRADER_CONTROL_ONLY`, `CIBO_MANAGED_RESEARCH_SETTLED`, `BROKER_AUTHENTIC_SETTLED`, `DEBIT_OPEN_COMMISSION`, `ADJUSTMENT`.
2. En la cartera manager con price path faltante, la racha futura será **UNKNOWN**, no 0 inventado ni 3 heredado; **ninguna decisión de nueva capitalización puede demostrar rendimiento si se conocen sólo los R Trader**.
3. Implementar máquina de estados de hair-cut separada de NAV: `NORMAL`, `LOSS_STREAK_PROTECTED`, `RECOVERY`, `RELEASED`; criterios de entrada/salida explícitos y auditados, para evitar castigo perpetuo. Política propuesta siempre versionada y testeada OOS; no presentar `una ganadora lo libera` como ley demostrada.
4. Comparar CONTROL (2782 haircut) vs CIBO-MANAGED (recalcular racha desde sus settlement auténticos) vs PAPER bypass sin filtros; no mezclar ledger entre brazos.
5. En no-live replay omitir el hair-cut de control si se investiga un manager sin liquidaciones CIBO; explicar el vacío de evidencia, no atribuir ventaja ficticia.

# 9. REPLAY AUTÉNTICO DE ADMINISTRACIÓN EN LAS 3.368

**El replay final debe recorrer el TIEMPO DE MERCADO, no hacer JOIN de tablas solamente.**

Obtener datos OHLC **ejecutables bid/ask** o ticks y fuente verificable para las seis series y todo el intervalo de exposición, ticks/precision, gaps, sesiones, timezone, comisiones/funding, histórico del instrumento. Calcular ATR de velas anteriores cerradas sin mirar futuro. La historia de `gross_structural_outcome_r` no sustituye este camino.

Motor ya iniciado `src/qore/infrastructure/cibo_managed_exit_replay.py`: `ExecutableOhlcBar`, `CiboExitPolicy`, `CiboManagedTrade`, `replay_cibo_managed_position`. Tiene tests de stop-first conservador, gap, partial, trailing/BE, defensa; **todavía no está conectado a las 3368 como motor de liquidación con NAV**. Estudiar y corregir ambigüedad intrabar, parcial 0.01 min residual, coste dos caras, fechas y eventos de órdenes.

**Secuencia obligatoria por evento causal:**
1. Cerrar y contabilizar operaciones cuyo precio ya activó TP, SL económico, parcial, trailing, BE o salida defensiva antes de evaluar la siguiente señal.
2. Debitar comisión OPEN en entry y fee CLOSE al settlement; un parcial requiere fee proporcional y lot grid de tramo + restante.
3. Poner NAV, PnL, equity broker, margen/reserva/fuentes actualizados, pérdidas consecutivas **de este brazo**; jamás arrastrar NAV de control a rama manager.
4. Ingestar señal Trader, invocar MAX Native cognitivamente con contexto actual **sin leakage**, producir acción explícita.
5. Cuatro motores económicos evaluar al MISMO epoch; QDLE valorar SL + fee + fuentes y generar lotaje real si físicamente viable. No filtrar Trader.
6. Registrar actuación de gestión a cada bar/price event; reducir riesgo y reajustar stops conforme a cognitiva; no fabricar fill ante falta de precio.
7. Hasta la última liquidación, revisar margen/Bank/Cushion/posición correlacionada, comisiones/swap y broker constraint en cada época.
8. Emitir informe por `signal_fingerprint`: `received, cognitively_reasoned, management_plan_created, qdle_risk_quoted, broker_simulated_fill, managed_partial_events, managed_exit, CIBO-settled_PnL, pending_reason, open_at_end`.
9. FINISHED requiere reconciliar 3368 señales, ejecutadas físicas <=3368, settlements + pendientes + no financiables=3368; cada faltante con motivo, sin resultados atribuibles a posiciones no simuladas.

**Trato de incertidumbre:** si no hay BID/ASK, etiquetar `NEEDS_PRICE_PATH` y cancelar el cálculo del PnL completo; NO usar R del Trader. Si precio toca SL y TP dentro de la misma vela sin ticks, stop-first conservador, sensibilidad a resolución; gaps ejecutan al precio abierto, no al stop ideal si peor.

# 10. PRUEBAS DE EFECTO COGNITIVO — OBLIGATORIAS

No bastan asserts de `joined=True` ni `native_max_mode_counts=3368`. Especificar pruebas `test_cibo_native_max_management_effect.py` y CI:

- [ ] **3368 señales de Trader recibidas**, sin ninguna omitida por racha, `COGNITIVE_BLOCK`, `CAPITAL_BLOCK`, OOS gate u otros policy veto. Mantener `signal_fingerprint` idempotente.
- [ ] **3368 evaluaciones Native MAX del motor REAL** + 3368 decisiones de administración con payload cognitivo (no etiquetas mapeadas) y evidencia de semántica / reloj.
- [ ] **Diferencia causal demostrable:** dos señales idénticas en precio/riesgo pero con evidencia cognitiva causalmente distinta producen distinto plan de SL/partial/trailing/BE/defense cuando la política prescribe cambio. Congelar entradas en un metamorphic test: al eliminar el plan CIBO, cambia alguna acción de gestión; de lo contrario FALLA.
- [ ] **Rechazar mapper fraudulento:** si se cambia únicamente `COGNITIVE_BLOCK→BANK` sin consumir variables de utilidad, incertidumbre, régimen, escenario y no aparecen decisiones distintas por señal, CI FALLA.
- [ ] **No admission:** ninguna `native_risk_decision` puede anular `TraderSignalIntake`.
- [ ] **Salidas de verdad:** replay con barras/ticks controlados demuestra diferentes cashflows vs `gross_structural_outcome_r` original, con casos adversos/stop-first/gaps, fee parcial, BE.
- [ ] **Compound source isolation:** inyectar 3 pérdidas `TRADER_CONTROL_ONLY` y comprobar que el historial `CIBO_MANAGED` NO activa `THREE_SETTLED_LOSSES_HAIR_CUT`; luego 3 pérdidas CIBO auténticas y comprobar que sí aplica bajo policy activa.
- [ ] **5% ALL-IN**, cada quote/posición, riesgo stop+comisiones/FX/buffer <=5% NAV de esa época; max exposure & min lot/step exactos, order_check/margen/fuente. Ninguna señal desaparece aunque el broker impida abrir.
- [ ] **Sin doble contabilización:** NAV, BANK, CUSHION, comisiones, margin held/released, parciales, múltiples trades a mismo timestamp, deduplicación.
- [ ] **No lookahead:** recortar toda evidencia futura y conservar idéntica decisión pretrade/gestión al mismo epoch; probar no leer settlement original para alimentar cognición futura.
- [ ] **UNIVERSAL:** seis símbolos y todos los Traders; error de símbolo sin alias real produce estado `REQUIRES_BROKER_EVIDENCE` sin perder la entrada.
- [ ] **Real vs shadow:** ningún proxy reclama fill MT5, PF/DD ni `certified=True`; la rama research no puede emitir `order_send`.
- [ ] **Crucial comparación:** correr 3368 full Native MAX manager real vs control y vs paper no-strategy-caps usando **mismos** precios y modelo de fees/broker, no dos universos distintos.

# 11. CRITERIOS CIENTÍFICOS PRE-REGISTRADOS

El objetivo antiguo 20% DD ideal / hasta 25% tolerable es aspiración; no garantizar ni maquillar. Evaluar:
- Recuperación de las 3368 señales: 3368 recibidas, 3368 evaluadas cognitivamente y 3368 con plan o pendiente explicado.
- Lotes físicos válidos (no propuestos abstractos), operaciones verdaderamente simuladas con bid/ask; comisiones OPEN vs CLOSE separadas.
- Equity curve manager, DD **mark-to-market intratrade**, closed equity DD, PF neto **>1.20** candidato, pérdida bruta por par, gross PnL, swap, win rate real, rachas administradas, máxima pérdida y tail gaps, concentración por Trader/símbolo.
- Cero riesgo presupuestado >5%, cero breach de soberanía/Bank/Cushion; eventual certificado requires proveedor verificado, OOS no usado para optimización y fuente de datos de mercado.
- **NO DEGRADAR EL TECHO** es objetivo de comparación respecto a estrategia económica coherente; **NO** comparar 3368 MARCLOSED con el viejo ceiling de `$670k` logrado por multiplicadores abstractos 10000x como si fuese broker physical QDLE.
- Hacer tres escenarios de capital inicial $60/$90/$120 sólo después de un manager causal y fuente broker consistente. No inventar ganancias y stops para «mejorar» la tasa de ejecución.

# 12. P0 — PLAN DE EJECUCIÓN DEL SIGUIENTE ARQUITECTO

**SECUENCIA ESTRICTA (NO INTERCAMBIAR NI QUEDARSE EN DOCUMENTACIÓN):**

### P0-A. Auditoría instantánea y cierre de la última ejecución
1. Ver HEAD rama y estado PR #745; verificar [#37912035662](https://github.com/mezas3238-hue/qore-core/actions/runs/37912035662). Registrar resultado del MAX fresh y guardar artifact SHA. Si falla por sensores/latencia/permisos, identificar exacto job/stack y repararlo. No afirmar «fresco» cuando se reutilizan recibos antiguos.
2. Comparar salida de cognitiva MAX **real** a nivel señal con el artefacto sellado. Verificar 3368 IDs, timestamps, causalidad y si la información rica contiene recomendaciones/acciones o sólo antiguo `capital_disposition`.

### P0-B. Reparación cerebro → administración
3. Sustituir el mapeador de etiquetas `classify_native_advisory` como **autoridad de la política** por `CiboCognitiveManagementDecision` derivada de episodios Native MAX verificados con entradas **causales**. Mantener etiquetas históricas sólo para auditoría.
4. Asegurar que el director real consulta MAX Native al recibir la entrada y durante la vida de posición, produce stop, riesgo, parcial, trailing, BE, defensiva con parámetros por señal **y razones**.
5. Conectar esta decisión al cálculo QDLE sin inventar "CIBO synthetic risk approvals". Caso sin trayectoria permanece SHADOW con motivo, sin declarar ejecución.

### P0-C. Eliminar bloqueos artificiales y neutralizar cashflow CONTROL en el manager
6. Eliminar de la **ruta experimental manager** gates de `COGNITIVE_BLOCK`, `CAPITAL_BLOCK`, `THREE_SETTLED_LOSSES_HAIR_CUT` alimentado de Trader control, votos discrecionales de motores que impidan `CIBO_MANAGEMENT_RECEIVED`. Mantener la rama **shadow sin restricciones estratégicas** separada y reversible; no borrar hard risk broker.
7. Dar procedencia de cashflow `CIBO_MANAGED_SETTLED`, separar ledger del CONTROL; ningún `recent_settlements[-3:]` con salidas Trader puede alimentar racha del brazo CIBO.
8. Añadir estados explícitos de retry/requote físicamente inejecutable y política de recuperación no perpetua. NUNCA presentar `0 unfundable` proxy como 3368 fills LIVE.

### P0-D. Trayectoria de precios, ejecución administrada y 3368
9. Buscar/obtener ticks o bid-ask OHLC históricos verificables para seis instrumentos y precio entrada→salida; indicar origen y sello. Si hay datos sólo para un subconjunto, simular legalmente ese subconjunto y reportar la cobertura; no falsificar el resto.
10. Integrar `cibo_managed_exit_replay.py` al scheduler global + cuatro motores + ledger Bank/Cushion + QDLE, con riesgo dinámico NAV **del manager**, comisiones reales y TP/SL adaptado. Verificar invariantes con instrumentación de cada señal.
11. Ejecutar el replay de **3368/3368 recibidas**, con contador separado de físicamente simuladas, SL nuevos liquidados y pendientes, y métricas de retorno **solamente donde la trayectoria sea completa y causal**.
12. Producir artefactos descargables: `full-trader-intake.json`, `native-cognitive-management-decisions.json`, `four-engine-capital-epochs.json`, `qdle-physical-volume.json`, `managed-position-events.json`, `CIBO-managed-settlements.json`, `NAV/DD/PF-evidence.json`, `missing-data-audit.json`, `comparison-control-vs-max-native-manager.json`.

### P0-E. Certificación posterior, broker y reporte
13. Verificar FundedNext/MT5 read-only specs, spread, tick size/value, contract, margin per lot BUY/SELL, swaps, comisiones debitadas en OPEN y CLOSE, min lot/step, stop-level/freeze-level y reglas proveedor. Ejecutar `order_calc_profit`, `order_calc_margin`, `order_check` con autorización apropiada; **NO `order_send` sin autorización explícita aparte**.
14. Entregar al CEO informe de resultados reales por símbolo, Trader, política, comisiones, gross/net, break-even/partials/trailing/defense, fuente Bank/Cushion, rachas y DD; **no declarar "trabajo terminado" mientras el cerebro siga limitado a mapeos estáticos o haya NAV tomado del control**.
15. Actualizar handoff, PR #745, links a commits, RUN ID/artefacto SHA, tests PASS/FAIL y decisión final SHADOW/NO LIVE.

# 13. ERRORES CONCRETOS QUE NO DEBEN REPETIRSE

- ❌ Medir solamente `max_native_mode_counts`, sin que el modo altere gestión real.
- ❌ Equivocar `received/quoted` con `broker filled` o posiciones administradas.
- ❌ Alimentar `THREE_SETTLED_LOSSES_HAIR_CUT` del manager con `REPLAY_SETTLED` del Trader control.
- ❌ Liquidar SL económico con `gross_structural_outcome_r` del SL antiguo.
- ❌ Desbloquear el mínimo 0.01 solo con `broker_min_stop_distance_price=0` y anunciar `3368` operaciones válidas para FundedNext.
- ❌ Heredar del escenario sin gestión el NAV para calcular las cuotas de nuevas operaciones del manager.
- ❌ Declarar `USD6.67`/DD93.20% como resultado de CIBO MAX Native gestor.
- ❌ Confundir `COGNITIVE_BLOCK` viejo con la decisión CIBO de gestionar conservadoramente.
- ❌ Convertir reglas estratégicas de four engines en otro selector de Trader, o quitar guardas físicas necesarias bajo el eslogan «sin restricciones».
- ❌ Repetir `MAX Native aprobó 11` como criterio de éxito; éxito es **3368/3368 administradas cognitivamente** y ejecución realista donde haya datos y solvencia.
- ❌ Considerar que tests unitarios de parciales prueban resultados del replay de 3368 sin dataset de precios.
- ❌ Presentar hash `sha256:` hecho con una cadena fabricada como firma/autenticación real de broker o de emisor CIBO.

# 14. MATRIZ DE TAREAS Y BLOQUEOS — ENTREGA DE CADA SUBARQUITECTO

| Frente | Dueño técnico | Prioridad y entrega |
| --- | --- | --- |
| CIBO A1, cerebro/trading | Native cognitive episode, director, position manager | **P0 absoluto** — episodios ricos -> decisiones concretas, acciones aplicadas a mercado, proof of cognitive effect 3368 |
| Motores A2 | Sizing, Compound, Adaptive Leverage, Portfolio | **P0** — no gates estratégicos en manager PAPER; capital causal real, separa cashflows control y manager, Bank/Cushion auditables |
| QDLE A3 | Motor físico, broker adapter, facturación MT5 | **P0** — lotes/SL/comisión/margen/FundedNext specs, 5% NAV, estados retry/requote, sin orden broker sin autorización |
| Integrador P0 (este handoff) | Timeline causal y prueba conjunta | **P0** — 3368 signals, native decision effects, settlements, NAV manager, comparación reproducible, CI/artifacts/handoff |

Todos los cambios primero branch/PR #745 y tests; coordinar sin sobrescribir otras ramas. No inventar que una rama de otro arquitecto ya está fusionada o que existe componente broker productivo en VPS.

# 15. CONDICIONES DE CIERRE — DEFINICIÓN BINARIA DE DONE

**NO ESTÁ TERMINADO si cualquiera es falso:**

1. [ ] 3368/3368 señales de Core recibidas e individualmente razonadas por Native MAX real.
2. [ ] `COGNITIVE_BLOCK` y `CAPITAL_BLOCK` NO eliminan del universo una señal Trader.
3. [ ] Existe `CiboCognitiveManagementDecision` no-trivial con semántica real y efectos trazables sobre parámetros/actions, no mapper estático de 1804/1553/11.
4. [ ] QDLE recibe los presupuestos coordinados y devuelve lotaje físico cuando legal, diagnóstico y opción de replan cuando no; 5% ALL-IN QORE NAV manager, fees OPEN/CLOSE.
5. [ ] Las entradas financiables y sus posiciones son administradas y salen por las acciones **CIBO** (no R Trader) cuando existe price path verificable; si no existe, ausencia de PnL claramente documentada.
6. [ ] CIBO Compuesto se alimenta sólo de settlements correctos de ese brazo; pérdidas del control no pueden volver a recortar el manager.
7. [ ] PnL/commission/DD/PF provienen de NAV manager y dataset bid/ask, DD MTM, y 3368 señales contadas por estado.
8. [ ] Cero omisiones, duplicados, futuros filtrados, falsos fills, órdenes LIVE no autorizadas o riesgo >5% presupuestado.
9. [ ] Tests de integración/causalidad obligatorios PASS; CI Actions SUCCESS con artefacto, SHA y descripción de toda limitación.
10. [ ] PR #745 actualizado y handoff final explícito con estado real, sin omitir fallos.

**QUÉ SIGNIFICA ÉXITO PARA EL CEO:** «La cognitiva CIBO MAX Native administra realmente el replay de las 3368 entradas junto con los cuatro motores y QDLE, sin filtros estratégicos, con responsabilidad económica y evidencia de cada entrada/salida». No basta que un informe diga «MAX Native consulted». No confundir la obligación de administrar el 100% de señales con una promesa matemáticamente imposible de ejecutar 100% de lotes.

# 16. DOCUMENTOS, CI Y ARTEFACTOS PARA NO PERDER CONTEXTO

- Handoff anterior: [`CIBO_SOVEREIGN_INTEGRATOR_P0_CONTINUITY_2026-10-08.md`](CIBO_SOVEREIGN_INTEGRATOR_P0_CONTINUITY_2026-10-08.md).
- CEO resultados manager+QDLE: [`CIBO_P0_3368_FULL_MANAGER_ECONOMIC_STOP_QDLE_REPLAY_2026-10-09.md`](CIBO_P0_3368_FULL_MANAGER_ECONOMIC_STOP_QDLE_REPLAY_2026-10-09.md).
- Auditoría Compound 2782: [`CIBO_P0_COMPOUND_2782_ROOT_CAUSE_2026-10-09.md`](CIBO_P0_COMPOUND_2782_ROOT_CAUSE_2026-10-09.md).
- Prueba sin topes: [`CIBO_P0_3368_PAPER_NO_STRATEGY_CAPS_2026-10-09.md`](CIBO_P0_3368_PAPER_NO_STRATEGY_CAPS_2026-10-09.md).
- MAX Native + QDLE: [`CIBO_P0_NATIVE_MAX_MANAGER_QDLE_3368_RESULTS_2026-10-09.md`](CIBO_P0_NATIVE_MAX_MANAGER_QDLE_3368_RESULTS_2026-10-09.md).
- Plan de gestión original de Trader y contrato: [`CIBO_P0_PARADIGM_OVERRIDE_2026-10-09_TRADER_EXECUTION_MANAGEMENT_QDLE.md`](CIBO_P0_PARADIGM_OVERRIDE_2026-10-09_TRADER_EXECUTION_MANAGEMENT_QDLE.md).
- Manager managed-exit path diagnostic: workflow [#37906585672](https://github.com/mezas3238-hue/qore-core/actions/runs/37906585672).
- Intermediación brain Native (anotación) + dos políticas: [#37911594114](https://github.com/mezas3238-hue/qore-core/actions/runs/37911594114).
- Re-ejecutar brain MAX fresco: [#37912035662](https://github.com/mezas3238-hue/qore-core/actions/runs/37912035662) — **ver estado antes de usar resultados**.
- [PR #745](https://github.com/mezas3238-hue/qore-core/pull/745) — conversación y seguimiento, no LIVE.

---

# 17. MENSAJE EJECUTIVO DEL CEO AL SIGUIENTE ARQUITECTO

**«ESTA ES UNA EMERGENCIA DE INTEGRACIÓN. ES INACEPTABLE QUE CIBO MAX NATIVE NO UTILICE TODA LA POTENCIA DE SU COGNITIVA PARA ADMINISTRAR CADA ENTRADA Y SALIDA DEL REPLAY DE LAS 3.368 SEÑALES. CIBO ES EL ADMINISTRADOR SOBERANO; QDLE CALCULA EL LOTE FÍSICO; LOS CUATRO MOTORES ECONÓMICOS COOPERAN, NO FILTRAN. NO QUIERO MÁS BLOQUEOS ARTIFICIALES SOBRE CORE. REPARAR DE EXTREMO A EXTREMO, REPRODUCIR LAS 3.368 SEÑALES Y ENTREGAR RESULTADOS QUE DE VERDAD CORRESPONDAN A LA GESTIÓN COGNITIVA DE CIBO. NO MÁS SIMULACIONES DE CIBO QUE SÓLO CAMBIAN ETIQUETAS».**

**Aviso del arquitecto saliente:** requisitos de solvencia/lotaje/5%/margen/fees/proveedor no se pueden falsear para aparentar 100% de fills. Defender integridad y seguridad financiera es compatible con la orden de NO FILTRAR señales de Core. La situación real es P0 ABIERTA, PR DRAFT, NO LIVE.

**PUNTO DE CONTINUACIÓN:** `scripts/cibo_p0_native_max_manager_advisory_3368.py` y `scripts/qdle_3368_dual_ledger_replay.py`, especialmente `classify_native_advisory`, `cibo_max_native_exit_policy_executed=False`, rama `manager_revised_stop` con quote-only, `recent_settlements[-3:]` del control; conectarlo a `cibo_native_max_cognitive_episode.py`, `cibo_managed_exit_replay.py`, cashbook Compuesto y tesorería QDLE. Antes: verificar #37912035662 y la procedencia de sus datos.

**NO DECLARAR CIBO MAX CERTIFICADO HASTA QUE ESTÉN REPARADAS ESTAS FALTAS.**

---

# ADDENDUM P0 — REPARACIÓN DE CÓDIGO REAL 2026-10-09 (NO CERTIFICACIÓN)

**NUEVO CHECKPOINT TÉCNICO OBLIGATORIO:** [CIBO_P0_NATIVE_MAX_QDLE_IMPLEMENTATION_CHECKPOINT_2026-10-09_CAUSAL_SENSORS_NO_CONTROL_PNL.md](CIBO_P0_NATIVE_MAX_QDLE_IMPLEMENTATION_CHECKPOINT_2026-10-09_CAUSAL_SENSORS_NO_CONTROL_PNL.md).

El arquitecto de continuidad realizó reparaciones en CÓDIGO y pruebas en GitHub sobre esta rama:

1. Run original #37912035662: **SUCCESS**; artifact **11609885185**, SHA256 `aeb47d8a0e234c2c01d3406b11c5ded55ccc0a156caa84ce9e1344a3485c635f`. Sigue siendo un resultado de recibos/etiquetas, no CIBO liquidando realmente 3368 posiciones.
2. El mapper ya no usa `COGNITIVE_BLOCK`, `CAPITAL_BLOCK`, `RISK_REVIEW_READY` para escoger modo de gestión. Consume `CALIBRATION`, `REASONING_ROUTING`, `SCENARIO_ENGINE`, `METACOGNITION`, `CAUSAL_REASONING` y `EXECUTIVE_SYNTHESIS`. La nueva política es un **adaptador temporal de investigación**, NO una decisión CIBO auténtica sobre lifecycle ni certificación MAX.
3. El presupuesto dinámico inferido de sensores se pasa al **QDLE físico** (risk request dentro del 5% NAV). Se probó una perturbación del sensor real con misma cuenta USD60/fee/modelo y lotaje QDLE 0.00 / 0.01 / 0.02. No se usan etiquetas anteriores como gate.
4. Se cortó el uso de PnL, `gross_structural_outcome_r` y rachas `REPLAY_SETTLED` del Trader CONTROL para establecer NAV y PnL de CIBO Native. **Todos los lotes Native del replay sin bid/ask completo quedan QUOTE_ONLY sin comisión OPEN pagada, sin ejecución ni settlement**. El NAV sintético de ensayo permanece USD60 pero capital final/PF/DD del administrador es **NULL / NO MEDIDO**, no rentabilidad cero.
5. Se añadió `scripts/cibo_p0_native_managed_exit_path_audit.py` para auditar salidas verdaderamente causales cuando se aporte bid/ask de la operación. Con datos sintéticos de test da resultados de SL/partial/BE/trailing/defense y no inventa R histórico ante cobertura incompleta. **Todavía NO mueve NAV global de los cuatro motores**; requiere scheduler de parciales y liquidaciones reales.
6. CI rápida (48 tests): [#37916235608](https://github.com/mezas3238-hue/qore-core/actions/runs/37916235608) PASS. Posterior [#37916291567](https://github.com/mezas3238-hue/qore-core/actions/runs/37916291567) PASS. El nuevo replay full [#37915676547](https://github.com/mezas3238-hue/qore-core/actions/runs/37915676547) seguía **IN_PROGRESS** al escribir este addendum: investigar inmediatamente logs/artifact final, **no presumir PASS**.
7. P0 sigue ABIERTO. Falta ejecutar / autenticar la decisión cognitiva nativa con órdenes económicas y ajustes intratrade, obtener trayectoria bid/ask histórica de 6 símbolos, scheduler con OPEN/CLOSE fee, NAV Bank/Cushion, métricas mark-to-market y conciliación MT5. NO LIVE, NO `order_send`, PR #745 DRAFT.

**Continuar SIEMPRE por el checkpoint enlazado primero**: contiene rutas exactas, commits, pruebas y medidas. El objetivo 3368/3368 significa **entregadas a CIBO**, nunca debe falsearse como 3368 fills cuando no son físicamente financiables.

---

# ADDENDUM P0 — INTEGRACIÓN DIRECTA CIBO SOBERANO ↔ QDLE (2026-10-09)

**NUEVO ESTADO VALIDADO — CÓDIGO P0 SHADOW, NO LIVE.** La conexión solicitada entre CIBO Soberano y QDLE se implementó en la API canónica con cuatro motores.

**Leer primero:** [CIBO_SOVEREIGN_QDLE_DIRECT_INTEGRATION_P0_2026-10-09.md](CIBO_SOVEREIGN_QDLE_DIRECT_INTEGRATION_P0_2026-10-09.md). Incluye contrato, rutas, 55 pruebas, lotaje físico 0/0.01/0.02 según cognitiva, origen de NAV y pendientes.

- Punto oficial `src/qore/infrastructure/cibo_sovereign_integration.py::administer_native_cibo_qdle_shadow`.
- Motor de acoplamiento `src/qore/infrastructure/cibo_native_sovereign_qdle.py::administer_native_sovereign_qdle_shadow`. Conserva la decisión económica original de CIBO (capital, cuenta, lane, SL, dirección), aplica solamente el riesgo Native MAX derivado de sensores causales, convoca los cuatro motores y ejecuta la reserva/quote física por QDLE; devuelve un recibo que actualiza el estado de CIBO como fundable/unfundable. NO broker fill.
- `scripts/qdle_3368_dual_ledger_replay.py` comparte ahora exactamente la función de riesgo cognitivo de la integración soberana. No replica otro motor de lotaje ni vuelve a introducir `gross_structural_outcome_r` al NAV del manager.
- NO SE ACEPTAN liquidaciones `TRADER_CONTROL_ONLY:`, `REPLAY_SETTLED:` o `REPLAY_PRIOR_CASHBOOK:` como `CIBO_MANAGED` en la nueva frontera.
- CI [#37932304931](https://github.com/mezas3238-hue/qore-core/actions/runs/37932304931): **SUCCESS 55 tests**, incluyendo CIBO Soberano→Native MAX→Sizing/Compound/Leverage/Portfolio→QDLE y retour lifecycle. Running/latest full #37932270093 debe verificarse de forma independiente y no se debe afirmar que ya terminó sin consultar el job/artifact.
- EL TRABAJO NO SE CIERRA como certificado mientras no existan instrucciones nativas autenticadas, feed broker real, trayectorias bid/ask y liquidaciones auténticamente modeladas de CIBO. Las 3368 señales son recibidas, NO 3368 fills. QDLE conserva siempre máximo dinámico 5% all-in, comisiones, vol grid, stop/margen/proveedor.

**PR #745 permanece DRAFT / NO LIVE.**
