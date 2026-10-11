# QORE Native — G0: preregistro de auditoría de fuente M1, SIN EDGE

**Fecha 2026-10-11.** Documento congelado antes del cálculo G0. Issue [#789](https://github.com/mezas3238-hue/qore-core/issues/789), charter [PR #790](https://github.com/mezas3238-hue/qore-core/pull/790). **NO se ejecutarán señales, retorno futuro, PF, Sharpe, DD o entrenamiento de IA en G0.** No se habilita operación ni presupuesto económico.

## Fuente fija

Solo fuente de provider-native M1, read-only, artefactos del GitHub Action [#35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), commit fuente `18c338aedd5013ce65a6cb6408ffbc2e904a6217`. Son **nueve símbolos** EURUSD, GBPUSD, USDJPY, AUDUSD, AUDJPY, GBPJPY, XAUUSD, USDCAD, NAS100, cada uno con artifact `qore-capitalizer-cibo-10y-native-m1-<SYMBOL>-<SHA>`; el artefacto es repositorio de datos de un proveedor, NO feed nuevo/OOS. El tramo analizado es `2025-09-17T00:00Z <= t < 2026-09-17T00:00Z`, ya usado en investigaciones anteriores y expresamente **NO independiente**.

### Contrato estricto de procedencia

Comprobar manifest en `native/m1-clone-manifest.json` contra símbolo de matriz; exigir flags `provider_native_m1=true`, `synthetic_m1=false`, `interpolated_m1=false`, `contradictory_m1=0`, `read_only=true`. Extraer identidad/esquema del lector neutral `capitalizer_cibo_m1_reader_v1.py`, solo como infraestructura, NO importar ningún detector, selector de trade o etiqueta económica de V49. Verificar campos de OHLC, fechas UTC, duración M1 exacta, chronological ordering estricta, precios positivos, high/low consistentes, dígitos válidos, volumen no negativo. Duplicado, corrupción o símbolos mezclados => job FAIL y estado de fuente INVALID, nunca simular candles faltantes.

## Métricas predefinidas (SIN retorno futuro)

Por símbolo:
1. Conteo total bruto M1, primer/último minuto, dígitos, tamaño del artefacto de GitHub (recuperable metadata), sha256 de manifest y sha256 determinista de archivos RAW_M1_LEDGER ordenados, identidad y flags de proveedor.
2. Dentro de ventana anual 365 días, M1 count por fecha UTC; total de fechas con >=1 registro, fechas hábiles (lun-vie), fin de semana, distribution mínimo/mediana/p05/p95 y máximo de M1 por día activo; **NO asumir FX 1440×cada weekday ni NAS100 24h**.
3. Mínimos temporales de presencia por hora UTC (0…23) separados weekday vs weekend, total observado y oportunidades nominales; incluir gaps internos entre M1 consecutivas en la misma sesión/día, clasificadas 1m / 2–4m / 5–14m / 15–59m / >=60m. **No llamar velas ausentes corrupción automáticamente** (horarios de mercado, rollover, domingos, feriados).
4. Cuatro celdas de disponibilidad preespecificadas, solo observabilidad de datos, **no evidencia de señal**: `EURUSD+GBPUSD` sincronizadas minuto a minuto, `AUDUSD+GBPUSD`, `AUDJPY+GBPJPY` y `NAS100` regular NY mañana, `XAUUSD` regular NY mañana. La sincronía relativa se medirá exactamente como intersección de minutos dentro del mismo UTC day, no como coincidencia de precios. Criterios de «full session» requieren calendarios fuente independientes y quedan PENDIENTES.
5. Por grupos de 15 minutos UTC y 60 minutos UTC: distribución de count de M1 observados entre buckets **activos** con 1–14 vs 15, 1–59 vs 60. Esto mide la calidad de agregación M15/H1 sin falsear 15/15 en horarios cerrados. H4 no autorizada en este gate.
6. No inferir costes de bid/ask, spreads, slippage ni capacidad de ejecución de un OHLC. Coste `UNAVAILABLE`, tick `UNAVAILABLE`.

## Interpretación / prereglas

- G0 `SOURCE_INTEGRITY_PASS` solo si manifest y M1 cumplen contratos, **aunque existan gaps por horario**.
- `COVERAGE_PARTIAL` si hay huecos de M1 en horas activas; no atribuir causalidad, investigar por proveedor/calendario; G0 aún **NO autoriza** estrategias si sus ventanas específicas carecen de densidad.
- `G0_PROVISIONAL_NO_SCHEDULE_CERTIFICATION` porque no se auditó calendario oficial de cotización ni sesiones de contrato por broker. Necesario para G1 formal.
- Cualquier ausencia de pares sincronizados es bloqueo SOLO para candidato RELATIVE en ese intervalo; DRIVE/RESET podrían continuar en otras ventanas.
- **No activar G1** hasta presentar el manifiesto por mercado y un preregistro separado del experimento/desenlace condicional por familia. Se prohíbe realizar regresión, optimización o señal retrospectiva dentro de G0.
- Si falta algún artefacto, reportar cada MARKET `ARTIFACT_UNAVAILABLE` sin inventar datos. Workflow separa markets (fail-fast false), no mezcla métricas ausentes.
- Réplica de datos o fuente adicional debe tener SHA, proveedor/periodo nuevo y disciplina OOS real; nada de llamar al histórico 2025–26 «holdout virgen».

**Este G0 puede producir resultados concretos sobre 9 mercados sin certificar ni una sola de las 3 hipótesis económicas.** Al finalizar se publicarán totales exactos, gaps, digest, sincronía entre pares y GO/STOP condicionado por calidad y cobertura, junto con el registro de los límites.
