# QORE NATIVE — PRE-REGISTRO G0 EXISTING12, AUDITORÍA M5 2016–2026 SOLO DATOS

**2026-10-11, PREVIO A CUALQUIER ANÁLISIS NUEVO DE RETURN / PnL.** Directiva Owner: comenzar I+D con **12 activos ya archivados**, incorporar **21 nuevos** solo tras adquisición y auditoría independiente. Congelar lista de 12, procedencia, reloj, datos permitidos y reportes antes de abrir resultados. Base de política [PR #814](https://github.com/mezas3238-hue/qore-core/pull/814), [Issue #815](https://github.com/mezas3238-hue/qore-core/issues/815). No operar noticias, no modificar VPS/MT5/CIBO/Shared/producción.

## Cohorte única y fuente inmutable

**Tres índices:** NAS100→USTEC, SP500→US500, US30→US30. **Dos metales:** XAUUSD, XAGUSD. **Cinco FX majors:** EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD. **Dos FX crosses:** AUDJPY, GBPJPY. **Exclusivamente los 12 símbolos preestablecidos**, sin ranking de desempeño ni selección post-hoc.

Fuente M5 archivada provider-native read-only cTrader DEMO, [GitHub run #35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458), commit productor `ab782b8e9f890f86a2b6500070f0556b4b685e3d`, artifact aggregate [#10476615509](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458/artifacts/10476615509) con índice hash **`47f5763d7ea2c10dd32fa40a84d7480c8124f1a512b623c1299ef2ba7b8c51c2`** y manifiestos correspondientes a 12 artefactos `qore-cibo-market-atlas-10y-windowed-<SYMBOL>-ab782b8e9f890f86a2b6500070f0556b4b685e3d`. Meta 2016-09-17T00 UTC → 2026-09-17T00 UTC (exclusive), **8.726.985 M5 producer-reported**. Comprobar sin confiar ciegamente en agregador. Los 9 subconjuntos con M1 nativa [run #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334) no se usan para sintetizar M5, tampoco se fabrican M1 para los otros tres.

## G0 auditoría rigurosa de datos, no resultados

Para cada artefacto exactamente original:
- Verificar `SYMBOL_SHA256SUMS.txt`, `MANIFEST_SHA256SUMS.txt`, `symbol-consumption-manifest.json`, 11 particiones anuales de 2016–26, `PARTITION_MANIFEST/YYYY.json`, `PARTITION_MANIFEST/YYYY.sha256`, `RAW_M5_LEDGER/YYYY.jsonl` y `DATA_QUALITY_LEDGER/YYYY.jsonl` **mediante SHA256 de contenido original** y por símbolo esperado, año, proveedor y origen.
- Recontar filas RAW M5, orden temporal monotónico UTC, `utc_timestamp_in_minutes`, alineación M5 minuto %5=0, pertenencia al rango/year/partición; rechazar duplicados y cualquier hash corrupto. Confrontar 12 manifiestos con aggregate inmutable; registrar first/last, huecos UTC no clasificados, 11 años, las discrepancias y tamaño original.
- **NO** calcular returns, direcciones, H/L económico, volatilidad, stops, patrones, señales, indicadores, precio de entrada, PF, Sharpe o PnL. Solamente auditar campos identidad+tiempo y hashes del archivo completo (SHA comprende OHLC pero el código no los lee como valores).
- **H4/D1 informe de disponibilidad, sin reconstruir precios:** evaluar bitmaps de timestamps por bloque UTC de 4h (48 M5 por H4) y día UTC (288 M5 por D1) solo si **existe al menos un M5**. Publicar número de bloques activos/completos/incompletos con huecos; días parciales NO equivalen a cierre de mercado validado. H4/D1 **UTC calendario y no definición de velas broker**; no declararlos como velas comerciables hasta definir sesión del instrumento, hora de rollover y DST. Contar **horas/días hábiles activos** por market observados, no extrapolar «número de trades».
- G0 no mide cobertura respecto a horario oficial porque falta archivo histórico de sesiones del broker. La clasificación `UNRESOLVED_CLOSURE_OR_MISSING_DATA` debe permanecer sin imputar. **El estatus CLEAN_PROVIDER_PAYLOAD del generador no certifica ausencia de cierres**.
- Guardar por símbolo JSON con SHA del manifest/producer/particiones, timestamp first/last, año → barras/huecos y H4/D1 completos de rango, flags read_only/research_only; generar agregación de doce sin edge / rankings.

**Estado de decisión**: `G0_M5_SOURCE_INTEGRITY_PASS` solo si 12 originales recuperados, 11/11 años/símbolo y SHA originales, secuencia UTC, raw recontado y source-map inequívoco. Si no, `SOURCE_PARTIAL` / `SOURCE_INTEGRITY_BLOCKED`, nunca sustituir datos. Este PASS sería exclusivamente G0 de estructura; **no** certifica calendario, spread BID/ASK, costes o cognitiva, ni permiso G1.

## Regímenes normales: dos capas independientes

- Futura capa de riesgo `NO_NEWS`: filtro calendario alto impacto conocido as-of, no abrir cerca del evento; políticas temporales de blackout aún **propuestas**, no validadas live. Cierre de posición pre-evento requeriría ejecución realista.
- Futura capa económica `MULTI_HOUR / H4 / D1`: UNA hipótesis con mecanismo económico y baseline preregistrados ANTES de abrir PnL, partición desarrollo/OOS, power efectivo por días o semanas, costes por horario/símbolo, robustez temporal. Nunca usar 12 mercados × N indicadores como búsqueda libre. Si no hay costes/sesión o potencia, marcar `G1_NOT_AUTHORIZED`.

## Cohorte pendiente

Otros **21 cTrader** bajo [PR #811](https://github.com/mezas3238-hue/qore-core/pull/811) son fuente separada y potencialmente DEMO broker distinto. **No entran a esta cohorte aunque aparezcan artefactos durante ejecución**; futura G0B de incorporación congelará artefactos/hashes/cobertura. No se concluye que estén descargados antes de su evidencia.

**Resultado esperado:** G0 con testigos reproducibles y sin resultados económicos. 0 traders certificados, cero live/VPS/MT5.
