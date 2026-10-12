# QORE Native — PREREG diagnóstico de spreads cero y simultaneidad BID/ASK, 2026-10-12

Derivado *después* de ver 5.727 snapshots as-of con bid=ask en el histórico corto de 29 instrumentos [QA #851](https://github.com/mezas3238-hue/qore-core/pull/851). **Estudio exploratorio de calidad de fuente, NO de ventaja económica.** No se modificará ni seleccionará ninguna de las 231 metodologías, ni hay test de PnL. Reutilizar únicamente artefacto original run #38283737706 / artifact #11762222336 con original SHA y 29 market manifests confirmados por #851.

## Preguntas congeladas antes de ejecutar este diagnóstico

1. Entre los snapshots BID/ASK de **precio idéntico** y ambos lados conocidos a tiempo `as-of` con máximo 5s de edad, ¿cuántos tienen **ambas actualizaciones en exactamente el mismo milisegundo**? ¿Cuántos tienen al menos un lado más antiguo en grupos (1..100ms, 101..500ms, 501..1000ms, 1001..5000ms)?
2. Reportar por **cada uno de los 29 mercados** y agregado, para no confundir una sola familia Forex con metales/índices.
3. Si los ceros son mayoritariamente simultáneos, NO concluir que el spread ejecutable es cero: separar problema de fuente/decodificación/semántica de broker de stale as-of. La prueba no identifica causa por sí sola.
4. Comparar con umbrales `0,100,500,1000,5000 ms` de ambos lados para un análisis de sensibilidad de captura **sin métricas económicas** y nunca calibrar estos umbrales ex post para seleccionar edges.

Mantener original SHA de ZIP y files, comparar al auditor fuente #851, output solo recuentos/porcentajes, nunca raw quote, señales, órdenes o trades. `COST_INFERENCE_BLOCKED` y `CERTIFIED_0_OF_3` independientemente del resultado. Conclusiones etiológicas requieren consulta técnica cTrader/IC Markets y testigo independiente. [Issue P0 #856](https://github.com/mezas3238-hue/qore-core/issues/856) contiene criterios de reparación. Almacenamiento Actions no es permanente, repo público no admite datos de broker brutos.
