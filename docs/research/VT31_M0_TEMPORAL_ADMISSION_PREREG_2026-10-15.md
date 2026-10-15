# VT31 — PRE-REG M0-A: puerta temporal y H1 antes del COG (15-Oct-2026)

**Rama:** `agent/vt31-m0-temporal-causal-admission-20261015` sobre #971 @ `0ec466784f3047849b6b0a479c18f68bb8bc3b41`.
**Fuente principal:** https://ttrades.com/the-am-silver-bullet-strategy-on-nq/ (H1 NY 09:00–10:00 cerrado; NY AM 10:00–11:00).
**Identidad:** ONE VT31, LONDON/NYPM ICT_GENERAL underdetermined; NYAM TTRADES_NY_AM_2025 como **elección RESEARCH no aprobada**. Esta especificación NO asigna permiso de orden/OMS.

## Hipótesis antes de código
La ruta investigativa #971 permite pasar `session` separado de `closed_m1` y no incluye una barrera pre-COG dedicada que exija que el último M1 esté exactamente en la ventana de NY asociada (DST incluido). Si un cliente pasa un identificador de ventana equivocado, la identidad de la fuente puede ser incorrecta. Asimismo, una H1 09 parcial en TTrades debe bloquear el procesamiento antes del productor; una secuencia pasada/futura/desordenada debe cerrarse sin juicio.

## Contrato causal preregistrado
1. La **admisión temporal** precede a `route_preselected_method` y a cualquier `VT31CleanroomCognition`; **ningún input inválido alcanza el COG**.
2. Exigir perfil tipado y `PREDECLARED`, `as_of` UTC-aware exactamente igual a último cierre M1, M1s tipados, orden ascendente estricto, no solapamiento, último M1 dentro de `window_bounds` por fecha local NY. Borde 11:00 NY válido solo para la vela 10:59 (análogamente London 03:59, NYPM 14:59).
3. Solo para TTrades NYAM: H1 de 09:00 a 09:59 NY con **exactamente las 60 velas M1 cerradas** y cada timestamp abierto esperado; detecta huecos, duplicados, mixed day o H1 todavía abierta. Si incompleta: `SOURCE_09H_INCOMPLETE_WAIT` (sin COG), nunca inferir el máximo/mínimo sobre H1 parcial.
4. Mal formato/ventana distinta/cronología/lookahead: `PRECOG_TEMPORAL_REJECT`, sin invocar ruta/COG. Una sesión source-unknown no es aprobación del autor.
5. Para entradas admisibles de #971, conservar resultados 4 `SUCCESS`, 4 `MIN10_CONFLICT`, 8 `ICT_UNDERDETERMINED` sin cambiar DOL, clasificación, sizing o PnL; no modificar COG/OPS/acta G3 protegidos.
6. `RESEARCH_CONTEXT_ADMITTED_NOT_CERTIFIED` solo significa validación temporal, **no** permite trading ni certificación. `original_cog_invoked` en #971 tiene una etiqueta de investigación, no constituye firma ni trazabilidad independiente de todas las ramas de retorno.

## Pruebas falsadoras predefinidas
- EST enero y EDT julio; 3 sesiones, dos direcciones y los 16 casos originales positivos/WAIТ/UNKNOWN.
- Adversarios: NYAM etiquetado London o NYPM, London como NYAM; último M1 fuera de la ventana, ASOF -1m/+1m, datetimes naive, stream invertido, barra duplicada, hueco o duplicidad en H1 09, H1 sin terminar, ausencia total, fecha futura.
- Al rechazar: usar monkeypatch del router con fallo explícito si llegara a ejecutarse, atestiguando PRE-COG. Sin optimizar tras observar retorno o modificar G3.

## Evidencia y alcance
Se publicará un workflow Python 3.12 con pytest paralelo y Ruff; hash de blobs G3 antes de ejecutar; JSON con 16 casos y contrapruebas, SHA256SUMS y artifact de CI. Una CI verde no da firmas COG/OPS ni fidelidad completa M3–M5, ni L3 Trader Lab, ni economic edge. No merge/live/OMS/ejecución/sizing.

**Criterio de evaluación:** cualquier caso adversario que invoque el router/COG será fallo; si algún caso #971 cambia su sentencia sin causa, será fallo. La ejecución de CI podrá ser consultada después de publicar; no declarar PASS antes de verla.
