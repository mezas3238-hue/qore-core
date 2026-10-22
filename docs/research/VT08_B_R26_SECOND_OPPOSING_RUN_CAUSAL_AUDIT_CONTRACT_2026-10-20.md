# VT08 B R26 — Contrato de segunda serie después de R25
Fecha: 2026-10-20. Estado: diseño de auditoría, NO certificación.

## Evidencia inspeccionada
Archivo real: src/qore/infrastructure/trader_lab/vt08_b_r25_ps_reanchor_and_cisd_reclaim_native_v1.py.
R25 verifica 10 M3 originales por C2, conserva SHA de fuente y censo, reancla el mínimo a min(run_low, CISD.low) y busca recuperación del nivel antiguo. Su salida fija reclaim_of_old_level_is_new_cisd=False y authentic_reformed_protected_swing=D_NOT_ASSESSED.

## R26 — implementación siguiente, sin inferencias semánticas
1. Congelar SHA y cardinalidad de los 2657 casos; conservar 107 muestra ciega y 15 sin recuperación, sin excluirlos.
2. En cada ruptura posterior del mínimo corregido, enumerar todas las series contiguas de cierres bajistas posteriores y anteriores al cierre C3, con IDs M3, source SHA y available_at.
3. Para cada serie candidata, exigir cierre posterior estrictamente superior a su apertura; registrar barra y reloj de confirmación. Si varias series satisfacen la geometría, marcar MULTIPLE_D, no escoger por PnL.
4. Separar los estados NO_NEW_OPPOSING_RUN, RUN_WITHOUT_CONFIRMED_BREAK, ONE_GEOMETRIC_SECOND_CISD, MULTIPLE_D, INSUFFICIENT_SOURCE. Un reclaim del nivel antiguo no basta para ONE_GEOMETRIC_SECOND_CISD.
5. Las 15 excepciones R25 quedan como casos negativos obligatorios y se comprueba si existe un cierre sobre el nivel de una nueva serie, no sólo sobre el CISD antiguo.
6. Validar con pruebas adversariales: CISD en última M3; vela confirmadora que fija mínimo; ruptura exactamente igual (no inferior); varias series; cierre simultáneo en C3; missing raw; timestamps fuera de orden; duplicados; cambio SHA; datos futuros.
7. Comparar la interpretación de la geometría con TTrades, relevante swing y POI auténticos mediante dos revisiones independientes A/B. Sin selector de fuente: WAIT/ABSTAIN.
8. Ninguna admisión cognitiva, fill, PF o certificación hasta superar gates de metodología, firmas reales y ejecución BID/ASK.

## Prohibiciones
No introducir QORE-alpha; no mirar PnL para seleccionar serie; no tocar holdout 7Y; no reinterpretar 301 reclaims como trades; no alterar sizing; no enviar LIVE/DEMO/VPS.

## Resultado de esta intervención
Se inspeccionó código R25 y se fijó contrato R26. No se ejecutaron nuevas pruebas originales ni se obtuvieron firmas independientes.
