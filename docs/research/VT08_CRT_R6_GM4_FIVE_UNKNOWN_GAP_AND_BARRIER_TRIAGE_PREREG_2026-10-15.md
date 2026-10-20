# VT08 CRT R6 — G-M4 cinco UNKNOWN, preregistro de diagnóstico sin cambiar contratos

Fecha: 2026-10-15. Resultado R5 preexistente: 108 G7 WAIT, TODOS asociados retrospectivamente a GM4 UNKNOWN previos; **NUNCA sustituir G7/G-M4 ni crear terminal**. Fuentes existentes, congeladas V3/G-M4, 139 eventos, 296372 velas M5.

Objetivo único: descomponer los cinco UNKNOWN originales ya identificados por G-M4 sin readjudicación económica y sin nuevos filtros de trading. La evidencia original G-M4 registra 2 UNKNOWN_ENTRY_ALREADY_BEYOND_BARRIER (1 AUDUSD, 1 USDJPY) y 3 UNKNOWN_MISSING_M5_BEFORE_TERMINAL (1 AUDUSD, 2 USDJPY). No se asume disponibilidad futura de barras inexistentes, ni que un precio anterior pueda cerrar una posición no abierta.

## Investigaciones causales de solo lectura, sin cambios de fuente

A. Entrada fuera de barrera: usando únicamente el open de la M5 que empieza exactamente en decision_clock (y los dos niveles congelados V3), detectar si la entrada estaba en/tras la invalidación, en/tras el destino o ambas. Es una descripción de inviabilidad geométrica y **NO convierte UNKNOWN en terminal probado**, ni crea un fill. No cambiar el comparador V3.

B. M5 ausente: buscar la PRIMERA vela M5 faltante en el intervalo decision_clock a cierre de C3 H4, y reportar reloj faltante, M5 previa presente y siguiente M5 disponible dentro de la misma C3, si existe. Determinar solo el hueco observable; sin imputar precios ni adjudicar cuál barrera tocó. Evitar ocultar vacaciones, cierres de mercado o proveedor sin metadatos autenticados.

C. Salida EX_POST independiente del ledger de decisiones: por mercado, case_id/source_event_id, categoría congelada, reloj y diagnosis, con flags “terminal sigue desconocido / no ingresos/capital”. Verificar que sumen exactamente 2 y 3 UNKNOWN por mercado, y no filtrar estos diagnósticos al G2 blind ni a G7 previo. No autorizar ningún nuevo trade, tampoco hipotético.

## Criterio de éxito
Casos 139/139 reconciliados; 5 UNKNOWN mantenidos, 0 suplantados, 2 outside-barrier, 3 missing M5. Nuevo test de dos geometrías y un hueco real sintético; failure si no concuerda G-M4. CI quality Ruff/mypy/pytest y los dos mercados Atlas originales. Salida agregada nunca equivale a G-M4 PASS.

No sizing de VT08, no lote ficticio, no R nominal, no PnL ni OOS; solo CIBO Risk posee riesgo patrimonial. G-M1..G-M4 PARTIAL, G-M5 NOT ISSUED, Global NO CERTIFIED.
