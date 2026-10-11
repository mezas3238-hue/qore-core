# QORE NATIVE G0B — prerregistro de cobertura horaria, DST y sincronía (sin retornos)

**Registro:** 2026-10-11; investigación exclusivamente de disponibilidad de M1. **Programa:** #789; **origen:** handoff PR #795, G0 audit Actions #38166675573 (11/11 success). **Rama aislada:** `research/qore-native-g0b-calendar-dst-synchrony-20261011`. **No VPS, MT5, live, producción, modelos de señales, resultados de retorno ni PF**.

## 1. Pregunta y frontera epistémica

¿Para qué fechas y minutos de *ventanas candidatas previamente definidas* existe una barra M1 nativa, completa y sincronizada? Esto **NO** demuestra que el proveedor permita negociar tales minutos. Las ventanas son relojes de investigación, NO sesiones oficiales de un broker. Las ausencias se clasifican `MISSING_UNATTRIBUTED`; no etiquetar un hueco como feriado, corte legal, rollover, outage, spread o falta de liquidez sin fuente de proveedor.

G0 ya examinó 2025-09-17 00:00 UTC a 2026-09-17 00:00 UTC excl. y halló M15 parcialmente activas y solapamiento >99% entre tres pares en minutos disponibles. Es muestra de desarrollo **previamente observada**, no OOS nuevo. No reetiquetar.

## 2. Fuente fija y garantías

Unicamente `qore-native-G0-<SYMBOL>-minute-bitmaps.json` para nueve símbolos, artifacts por mercado del **run 38166675573** con commit de ejecución `fb22970798a2bd93f097f1327ce9c864eec0bb9c`. Archivo `days`: día UTC → máscara hexadecimal de 1.440 bits; bit 0 corresponde a 00:00 UTC y bit 1439 a 23:59 UTC. Confrontar símbolo y unicidad, longitud de bits, count por fecha y fuente G0, sin leer OHLC, precios, trades, resultados ni futuros. No reusar detectores ICT, TTrades o V49. Versiones y digest de artefactos para reproducción.

## 3. Ventanas nominales fijas (fecha local, lunes–viernes)

| Código de ventana | Zona IANA | Inicio inclusivo, fin exclusivo local | Símbolos / uso |
|---|---|---|---|
| `DRIVE_NY_AM` | America/New_York | 09:30–11:00 | NAS100, XAUUSD, EURUSD, GBPUSD |
| `RESET_LDN_FIX_CONTEXT` | Europe/London | 15:45–16:15 | EURUSD, GBPUSD, USDJPY |
| `RELATIVE_LDN_AM` | Europe/London | 08:00–12:00 | EURUSD/GBPUSD, AUDUSD/GBPUSD, AUDJPY/GBPJPY |
| `RELATIVE_NY_AM` | America/New_York | 09:00–11:00 | mismos tres pares |

**Significado:** WMR Closing Spot establece benchmark a las 16:00 Londres; la franja ±15 minutos anterior es una ventana **QORE de auditoría de presencia**, no ventana WMR oficial ni autorización para operar. Fuente metodológica WMR: https://www.refinitiv.com/content/dam/marketing/en_us/documents/methodology/wm-refinitiv-methodology.pdf . CME E-mini y COMEX GC tienen sesiones oficiales propias, **no intercambiables con NAS100/XAUUSD spot/CFD del feed**: https://www.cmegroup.com/articles/faqs/micro-e-mini-equity-index-futures-frequently-asked-questions.html y https://www.cmegroup.com/markets/metals/precious/gold.timeAndSales.html . Identidad, broker, venue, zona, feriados y reglas del proveedor quedan `NOT_VERIFIED`.

No excluir feriados ni cierres especiales por hipótesis. Cada día local laborable se cuenta como nominal; un día ausente se incluye en denominador y se etiqueta sin atribución, sin reinsertar M1 sintéticas. El posible sesgo de denominador de calendario se documenta, no se oculta.

## 4. Endpoints exclusivamente de cobertura

Para cada mercado×ventana: número de fechas nominales; minutos nominales; minutos M1 presentes; ausentes; ratio presente; número de días 100% completos; 95%–99.99%; <95%; fechas completas; fechas con huecos y pares bitmaps UTC. Para pares: sólo intersección estricta del mismo minuto UTC, número de fechas 100% doble-pierna, parcial y no disponible. `eligible` **solo quiere decir disponibilidad ex-post para analizar esa cohorte**. No implica negociabilidad ni que una feature de varios minutos pueda calcularse antes de estar cerrada. Publicar conteos de 15/15 y 60/60 cuando los buckets caben completamente dentro de ventanas candidatas; no usar un bloque incompleto como cerrado.

**DST fixtures congeladas antes del estudio:** NY 09:30 = 14:30 UTC el 2026-03-06, 13:30 UTC el 2026-03-09; Londres 16:00 = 16:00 UTC el 2026-03-27, 15:00 UTC el 2026-03-30. Comparar timestamp exacto y fechas sin cambiar el calendario a posteriori.

## 5. Motivos, decisiones y gates

`OBSERVED`, `MISSING_UNATTRIBUTED`, `CALENDAR_UNVERIFIED`, `BROKER_CONTRACT_UNVERIFIED`, `COSTS_UNAVAILABLE`, `PAIR_LEG_A_MISSING`, `PAIR_LEG_B_MISSING`, `BOTH_MISSING`; los códigos de missingness describen observación, no causa económica.

- `SOURCE_OBSERVABILITY_REPORTED`: todos los outputs computables, integridad bitmaps y tests DST pasan. Esto **no es G0B certificado**.
- `SOURCE_PARTIAL_PROVIDER_UNVERIFIED`: estado obligado mientras identidad/horario/feriados del broker y precios negociables estén sin documentar. Cada símbolo conserva un campo de verificación.
- `SOURCE_BLOCKED_INVALID_BITMAP`: máscara corrupta o inconsistencia con G0, no imputar.
- `G1_DATA_REVIEW_REQUIRED`: ventanas con cualquier missingness; desglose íntegro por día antes de seleccionar cohorte. No declarar elegible para un test económico una fecha incompleta sin política de censura preregistrada.
- **STOP certificación económica:** sin costes broker observados, true OOS y venue probado no hay certificación; G1 geométrico/descriptivo puede planificarse con etiqueta exploratory bajo prereg independiente.

Una segunda etapa manual debe enlazar para cada símbolo el instrumento EXACTO en broker (contrato, servidor, zona horaria, spreads bid/ask por hora, trading breaks, días festivos) con evidencia fechada antes de cambiar `CALENDAR_UNVERIFIED`. Prohibido asumir CME == NAS100 CFD, GC == XAUUSD CFD o tasa WMR == operaciones broker.

## 6. Entregables y no promesas

Código determinista + tests (bitmask, lunes–viernes, DST UK/US, cero no imputado, pares + buckets) + workflow GitHub que descarga artefactos G0 por run ID, audit JSON por mercado/ventana, informe con denominadores y n de fechas y enlaces a Actions; publicación de #789/#792/#793/#794 tras corrida satisfactoria. **Todavía 0/3 traders certificados, G1 sin resultados, 0 PF nuevos.** No lanzar optimización ni P&L desde G0B.
