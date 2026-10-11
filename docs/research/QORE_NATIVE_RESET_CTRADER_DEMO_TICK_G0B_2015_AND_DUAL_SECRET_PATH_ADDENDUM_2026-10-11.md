# QORE RESET G0B — addendum pre-tick de 2015 y arbitraje seguro de credenciales

**2026-10-11.** Registrado DESPUÉS del fallo de autenticación #38177511169, **ANTES de cualquier tick recuperado**, de cualquier lectura de precios y de cualquier prueba económica RESET G2. El prerregistro G0 original de 2016–2026 no se edita ni se oculta. Este documento agrega explícitamente una fuente histórica identificada después por el propietario.

## Motivo documentado, NO sobreajuste económico

El programa CIBO de [run #36367221571](https://github.com/mezas3238-hue/qore-core/actions/runs/36367221571), completado con 21/21 jobs en 2026-09-28, conserva M1 EURUSD `2014-08-27..2016-09-17` (762.455 M1), metadata artifact #10948728912, source EURUSD M1 artifact #10948342218. **No abrir OHLC ni utilizar el holdout**: los metadatos confirman EURUSD disponible en 2015 pero no ticks. Por tanto la prueba de cobertura cTrader BID/ASK puede incluir también **primer martes local Europe/London >=15 septiembre de 2015**, **2015-09-15**, ventana 15:45..16:15. El censo será 12/12 (2015–2026). No cambiar por ninguna razón las ventanas antiguas ni el método de selección, solo extender retrospectiva temporal una vez a petición expresa del dueño.

La ejecución previa #38177511169 pasó 9 tests, app auth cTrader, falló `ProtoOAGetAccountListByAccessTokenReq`, **cero ticks**. Los workflows antiguos `.github/workflows/qore-capitalizer-pre2016-sealed-holdout-v1.yml` priorizaron alias genéricos `QORE_CTRADER_CLIENT_ID/SECRET/ACCESS_TOKEN` antes del par `QORE_CTRADER_DEMO_*`, al contrario de la PR #803 que daba prioridad al alias DEMO. No sabemos si todavía contienen tokens distintos/válidos. **Hipótesis de infraestructura**, no de mercado: la ruta de secrets seleccionada puede explicar el bloqueo.

## Dos rutas autorizadas; cero secretos visibles

- Probar bundles completos `GENERIC_SECRET_ALIAS` y `DEMO_SECRET_ALIAS`, en ese orden, cada uno formado por su propio `CLIENT_ID`, `CLIENT_SECRET`, `ACCESS_TOKEN`. No cruzar tokens con otra aplicación. Si ambos son idénticos, probar solo una vez.
- Toda sesión utiliza `demo.ctraderapi.com`, identificación de la cuenta por `isLive=false`, alcance VIEW(0)/TRADE(1) para **solo consultas** y cotejo de EURUSD contra el ID simbólico archivado de CIBO. Jamás enviar órdenes, consultar LIVE o rotar refresh tokens.
- Si falla la primera ruta, cerrar sesión antes de intentar la segunda. Clasificar razón de fallo en categorías o código provider estrictamente sanitizados, jamás mostrar tokens ni IDs privados. Si fallan ambas, `AUTH_BLOCKED`, **cero ticks**; no atribuir automáticamente causa al proveedor.
- Respetar el original de las 11 fechas; el addendum agrega 2015, no da permiso para modificar el endpoint económico G1, analizar holdout, seleccionar sesiones rentables, ni abrir DRIVE/RELATIVE.
- `SOURCE_G0_CANDIDATE` solo con BID y ASK **completos** en las **12 fechas**, sin `hasMore` irresuelto y SHA por archivo. 12/12 no garantiza aún cobertura continua de todos los fixings. 0/12 no prueba falta de historia, solo imposibilidad de acceso.
- **GitHub-only**, ninguna copia de credenciales en archivos/artefactos. El operador debe actualizar secrets directamente en GitHub si ambos tokens son inválidos; este workflow nunca puede hacerlo por sí solo.

Este addendum altera únicamente *evaluación de acceso y amplitud temporal de inventario*, antes de existir ticks. Es criterio G0B, no segundo ensayo económico.
