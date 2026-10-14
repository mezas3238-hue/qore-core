# VT31 MC-P1 · Prerregistro: contrastar el COG REAL contra la fuente TTrades AM sin reescribir ICT (2026-10-14)

## Motivación y corte temporal

Continuar [PR #926](https://github.com/mezas3238-hue/qore-core/pull/926): el comprobador M0–M3 construye DTO sintéticos y pasa 13 tests, pero todavía NO demuestra que el COG auténtico cumpla TTrades. **Antes de crear los experimentos de COG real** registrar esta prueba falsable: no introducir filtros de rentabilidad ni cambiar su lógica después de observar salidas. Mantener G3 r1.3 doc SHA `a446afa17ed6e411b8f0b6fc182b103a78959a97`, código SHA `78d4cdac0e09d1a6eef37b99c505ffc5098031fc` intactos; #897 firmas sigue abierto.

## Fuente y perfiles — no atribuir TTrades a todas las sesiones ICT

- Base ICT GENERAL 2023: [Silver Bullet video](https://www.youtube.com/watch?v=tRq1hyGGtl4), sesiones London, NY AM, NY PM; no imponerle universalmente el H1 09:00–10:00 NY AM de otro autor.
- Variante autoral TTrades NY AM 2025: [ttrades.com fuente](https://ttrades.com/the-am-silver-bullet-strategy-on-nq/), high/low H1 09:00–10:00 NY, sweep LOW→LONG o HIGH→SHORT seguido de desplazamiento de retorno dentro del H1 y DOL al lado H1 opuesto; familias de entrada y stop no cubiertas por MC-P1.
- Perfil QORE G3: MSS de pivote M1/umbral 1,25×mediana5 y DOL entre prior cash/Asia/London. Su software puede ser causal sin concordar con TTrades.

## Ensayo contrastante preregistrado MC-P1

**Inyectar a `VT31CleanroomCognition` real `G3_MSS_FRAMEWORK_POLICY`**, con exactamente una sesión previa cash 390 M1 completas, Asia 00–03, London 03–05, continuación 05–09, una barra H1 09–10 completa (60 M1), y 6 M1 desde 10:00 NY. Datos sintéticos: fecha NY enero 2026 EST; referencia 09 high 110 / low 90, barras 10:00–10:06 nunca superan high ni penetran low; pivote/MSS M1 causal favorable LONG a 107 y DOL previo NY high 150. Confirmar H1/M15 frescos y DOL unswept. COG no requiere el 09H1 raid. Dos desenlaces ex ante permitidos:
1. Si COG devuelve LONG: pasar su **DTO real, sin alteración** al testigo source de PR #926. Esperado `REJECTED` por `NO_PRE_SIGNAL_9AM_H1_SWEEP` y `DOL_NOT_OPPOSITE_9AM_H1_EXTREME`; así se acredita que **COG QORE NO ES réplica doctrinal de TTrades** en esta situación. No afirmar que ICT GENERAL falla.
2. Si COG no devuelve señal: registrar missing y ajustar SOLO fixtures para que haya MSS causal a partir del patrón ya documentado en tests originales, sin tocar código del modelo ni reglas. No seleccionar sample usando resultados financieros.

**Pruebas adversariales adicionales**: cada modificación de DTO/DOL o de hechos cerrados debe fallar el perfil correcto; London e NY PM no deben ser vetados por 09H1 propio de TTrades; as-of no puede consumir velas posteriores, sin pruebas económicas, sin órdenes, sin test de holdout. Conservar recuentos de testigos, estado `COG_TTRADES_AM_SOURCE_NOT_CERTIFIED`.

## Declaración de alcance de certificado

Un resultado `PASS` de pruebas MC-P1 sólo confirma **detección correcta de una frontera doctrinal específica** y control de causalidad, no metodología ICT completa, no neurocognición total, no rentabilidad. Estado máximo `M0_M3_EVIDENCE_ENHANCED_METHOD_COG_PENDING`. Para promover se requerirán M4 familias reales FVG/OB/Breaker con testigos no ambiguos, M5 salida por fuente, revisión M6, y M7 economía/holdout. NO MERGE, NO MAIN, NO LIVE, NO VPS, NO QDLE y sin lotaje propio.
