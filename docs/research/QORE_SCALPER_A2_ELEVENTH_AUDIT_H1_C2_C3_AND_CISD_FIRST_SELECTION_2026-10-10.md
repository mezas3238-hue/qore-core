# QORE SCALPER — A2 Undécima auditoría, adjudicación metodológica P0

Fecha: 2026-10-10. Repo mezas3238-hue/qore-core, PR #759 DRAFT, rama agent/scalper-architect-b-methodology-20261010.

**Veredicto: NO CERTIFICABLE. Method-first freeze. No filtros, no nueva arquitectura World Model, no VPS, MT5, LIVE ni merge.** V49 permanece congelado como baseline de *investigación histórica*, NO una simulación causalmente certificada.

## 1. Rectificación de H17: 8,3% C3 NO mide fidelidad 8,3%

Fuente TTrades primaria exacta, 7 febrero 2026, "Establishing Hourly Bias": https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/ . Establece **cierre Candle 2 O Candle 3** para sesgo H1, en conexión con interacción de liquidez/POI/FVG y subsiguiente M15/M1. El artículo "Candle 3 Closure" de diciembre confirma que C3 opera cuando C2 falla: https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/ .

Evidencia nueva GitHub Actions **#38096345552 11/11 SUCCESS**, nove mercados; el censo de V49 source-ID congelados no usa outcomes ni cambia órdenes:
- 2876 oportunidades fuente reconciliadas;
- **2638** eventos H1 etiquetados CANDLE2_REVERSAL (**91,7%**);
- **238** eventos H1 etiquetados CANDLE3_CONFIRMATION (**8,3%**);
- **1604** oportunidades con SESSION_INHERITED H1 state (**55,8%**), **1272** no heredadas.

Por tanto la afirmación "**91,7% no proviene de la Candle 2/3 closure TTrades**" es **REFUTADA a nivel de etiquetas**. Esto NO prueba fidelidad autor a nivel POI/closing M15/M1. La falta de cobertura de H1 exact 60/60 en la auditoría anterior y la diferencia entre source event y session-start heredado hacen inválido tratar "1460 witness" como porcentaje de fidelidad.

**Implementación real verificada por lectura:** _build_h1_bias_events en capitalizer_generic_scalp_census_v48.py genera C3 usando detect_candle3_confirmation si C2 anterior no estuvo confirmado con POI compatible, y genera C2 reversal con sweep de extremo previo + cierre de vuelta al rango + POI compatible; V49 hereda señales como V49H1ContextState en capitalizer_h1_context_state_v49.py. Este es un *censo de firma de implementación*, NO source-certified proof de que el POI causó la apertura de la serie ni de que estado H1 sigue válido. El diseño QORE sólo implementa C2 reversal en esa función: si el texto del autor permite C2 continuation en la ruta genérica, se debe adjudicar por contexto antes de modificar señales.

**H17 refinada:** H17a POI C2/C3 de cierre fuente inválido/mal enlazado; H17b estado H1 heredado no revalidado al timestamp M1; H17c timing M15→M1 no implementa el protected swing de TTrades. Ninguna tiene un N de fracaso confirmado. No imponer filtro.

## 2. CISD: diferencia reproducida, separar primera selección de EXISTENCIA de candidato

Run 9market anterior **#38095562104 SUCCESS** 2876/2876:
- 2495 FULL_WINDOW y PREFIX coinciden.
- 381 difieren (247 sensor antes otra familia, 134 mismo close otra familia).
- Recalcular misma pareja de observadores sobre ventana histórica completa reproduce V49 exactamente 2876/2876; cerrarlos en prefijo M1 original reproduce sensor 2876/2876.

**Causalidad:** el selector V49 de PRUEBA histórica no es *prefix-invariant* para 381. Esto es un defecto del **criterio de selección del primer evento** con conocimiento posterior, no demuestra automáticamente que el evento V49 no tuviese un testigo válido al instante de cierre. Una familia puede estar disponible como candidata aunque otra hubiese sido seleccionada como primera online. Tampoco las 2495 coincidentes prueban fidelidad POI/H1, sólo reproducibilidad de la selección bajo ambas ventanas.

Nuevo validador capitalizer_scalper_a2_eleventh_cisd_prefix_membership_v1.py: por cada fuente registra (a) primer evento seleccionado online, (b) primer evento visto por observador de la *misma ruta* en prefijo, (c) si el evento fuente estaba dentro de **todas las candidatas** = UNKNOWN hasta enumerarlas exhaustivamente. Jamás sustituye UNKNOWN por un binario falso de lookahead-event, ni usa MFE/MAE. Tests incluyen contraejemplo donde Sweep temprano compite con FVG disponible al cierre, y ruta fuente difiere de primera seleccionada online. Workflow de prueba 9market qore-scalper-a2-eleventh-cisd-membership-nine-market.yml.

Para elevar la categoría a **lookahead original-event CONFIRMADO POR ID** hay que construir un enumerador independiente de TODOS los testigos CISD candidatos, con close/serie/POI/swing y los timestamps de formación, hasta source.decision_at. En ese entonces:
- SOURCE_EVENT_ASOF_PRESENT = existe el evento V49 en conjunto causal, aunque no sea la primera opción.
- SOURCE_EVENT_ASOF_ABSENT_WITH_COMPLETE_ENUMERATION = no existe, y sólo entonces se puede etiquetar ausencia real / posible lookahead evento.
- INCOMPLETE / POI_UNATTESTED = NO EVIDENCIA, no falsificar ausencia.
Las 381 no son rechazo automático: un filtro mecánico previo empeoró PF/DD y ganadores.

## 3. Reanálisis PRE-REGISTRADO del subconjunto causal y economía

Usar el libro fuente V49 original con IDs y la conciliación por familia en dos grupos **2495 coincidentes** y **381 no prefix-invariant**, y distinguir el subconjunto realmente ejecutado MAX3 original: 2020 trades, PnL bruto, y sus IDs. N en cada estrato se calcula y reporta, NO asumir 2495 trades ejecutados. Recalcular favorabilidad H1 +15/30/60, Sweep→CISD +30 min, MFE/MAE y geometría de target con cobertura efectiva y el mismo ID/cierre para comparar; intervalos por fecha NY. Tales reanálisis siguen siendo **diagnósticos post-hoc**, no sustituyen replay físico.

Antes de cualquier PF/DD de una alternativa: construir evento ONLINE emitido en cada M1 cerrada, sin conocer siguiente M15 ni fin H1 futuro, seleccionar primera tesis/familia por regla fuente-fiel; respetar portafolio MAX3, stops/targets, intrabar STOP-FIRST, salidas sesión, memoria elegida/settled-only. No escoger política nueva por retornos in-sample. Desagregar original gain identity (>=934 IDs y >=415.74848565R original) con densidad; requisitos OWNER no son reglas del autor. Requerir proveedor independiente y OOS congelado para certificación. No comparar R brutos como DD porcentaje ni inventar BID/ASK/comisiones.

## 4. Transferencias entre arquitectos

A2 #757: source-ledger C2/C3, POI/HTF, 381 per-ID e implementación streaming sólo tras verificar autor. A1 #756: mantener nuevo World Model congelado, conservar puerto Master cognitivo existente, proteger paso de indicadores outcome-blind y NO ingresar ventana completa / resultados futuros a Master. Los dos tracks conservan PRs DRAFT y V49 inmutable. No publicar PF/DD full Master mientras falte replay económico real.


## 5. RESULTADO EMPÍRICO P0 — 381 CISD no son 381 eventos ausentes del prefijo M1

[GitHub Actions #38096548896 — 11/11 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/38096548896) y [artifact agregado #11686545003](https://github.com/mezas3238-hue/qore-core/actions/runs/38096548896/artifacts/11686545003), 9/9 mercados, ledger por 2876 IDs reales. Resultado:
- **2495/2876** fuente V49 = *primer candidato seleccionado globalmente* en el prefijo online.
- **381/2876** fuente V49 ≠ primer candidato globalmente seleccionado online. Un replay del policy V49 full-window NO es prefix-invariant en estos 381 IDs.
- **2876/2876** el **observador original de la misma ruta** (Sweep o FVG) devuelve la **misma CISD al close original** en el M1 PREFIX, incluidos los 381; 0 no atestados por el observador de su propia ruta.

**Adjudicación de la petición de la undécima auditoría:** ninguna de las 381 discrepancias constituye evidencia de que la CISD original fuera físicamente indetectable al close bajo el observador QORE de su propia ruta. El defecto encontrado reside en la **primera selección global / prioridad efectiva de dos observadores no prefix-stable**, y no en la existencia del evento original QORE. El cierre es reproducible por ruta, pero aún falta comprobar que el swing y la serie están ligados al POI HTF de TTrades y que la política de selección online autor-fiel produce ordenes cronológicas correctas.

**No inferir:** que 381 no causales deban vetarse, ni que 2876 son íntegramente fieles al autor por la sola coincidencia de detector de QORE. Continúa NO CERTIFICABLE; el PF/DD V49 bruto histórico NO se convierte en replay live-causal certificado. Cualquier etiqueta de event-lookahead independiente de la fuente requiere más prueba. El siguiente test debe recorrer los candidatos *en cada close M1*, mantener primera selección fijada, y comprobar densidad/PF/DD con economía real y MAX3 global.
