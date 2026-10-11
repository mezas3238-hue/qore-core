# QORE Native DRIVE NAS100 G1 — ejecutado con CIBO M1 — resultado NEGATIVO

**2026-10-11. Veredicto congelado: `DEV_DRIVE_GROSS_NO_SUPPORT`.** Estudio inicial de persistencia de precio, **un solo horario y un solo mercado**, sin parametrización posterior. Se conserva íntegro el preregistro pre-outcome, commit `9ebcf60628196a52cbd476e584d4f554b60af035`. **No refuta toda la continuación**, solo la identidad económica y control de este piloto. Datos 10Y ya consumidos; NO OOS virgen.

## 1. Testigos inmutables

- PR [#805](https://github.com/mezas3238-hue/qore-core/pull/805), rama `research/qore-native-drive-nas100-open-continuation-g1-20261011`.
- Preregistro pre-resultados: `docs/research/QORE_NATIVE_DRIVE_NAS100_G1_SINGLE_CLOCK_PREREG_2026-10-11.md`, SHA commit **`9ebcf60628196a52cbd476e584d4f554b60af035`**. Código `src/qore/infrastructure/trader_lab/qore_native_drive_nas100_g1_v1.py`, tests `tests/infrastructure/trader_lab/test_qore_native_drive_nas100_g1_v1.py`, workflow `.github/workflows/qore-native-drive-nas100-g1-cibo-m1.yml`.
- [**GitHub Actions #38185670105**](https://github.com/mezas3238-hue/qore-core/actions/runs/38185670105): **2/2 jobs SUCCESS**; `quality` 9/9 pytest, Ruff PASS; `study` SOURCE + BIDIRECCIONAL G1 completado. SHA de código **`e20aa8e3b069f4f8e4e4d3d9915c1351075feae4`**.
- [**Artifact resultado #11719487773**](https://github.com/mezas3238-hue/qore-core/actions/runs/38185670105/artifacts/11719487773). Incluye `drive-g1-out/drive-g1-nas100-report.json`, `drive-g1-out/drive-g1-nas100-day-pairs.jsonl` con 2.547 fechas, SHA de reporte, SHA de filas y `OUTPUT_SHA256SUMS.txt`.
- Original cTrader DEMO **NAS100=USTEC** M1 10Y desde [CIBO Actions #35548099334](https://github.com/mezas3238-hue/qore-core/actions/runs/35548099334), artefacto **#10618862813**, commit productor `18c338aedd5013ce65a6cb6408ffbc2e904a6217`. Manifest SHA **`afdc85a380843cba7a4a10120a02233b6f248cdb046c7bf300dcb57fed8e69b0`**. `RAW_M1_LEDGER` 11 años SHA256 verificados sin re-descarga; **3.486.929 velas M1 nativas**, 2016-09-17 UTC a 2026-09-17 UTC exclusivo, `digits=2`, 0 contradicciones de OHLC/tiempo. La fuente sellada anterior a 2016 no se abrió.

## 2. Pregunta y frontera causal (sin cambios)

- Señal: `sign(ln(open 10:00 / open 09:30))` ambos **America/New_York**; el segundo precio se observa antes de la supuesta entrada de las 10:01.
- Retorno bruto: `Y=10000*ln(open M1 11:00 / open M1 10:01)` bps log; no asumir precio BID/ASK ejecutable ni comisión. Exige **91/91 aperturas M1 reales consecutivas** 09:30..11:00, misma fecha NY y hora con DST correcto.
- Placebo causal: usar el signo de la formación del **último día observado y completo ANTERIOR**, siempre de antigüedad **≤5 días naturales**, pero multiplicado por el MISMO Y actual (exacto mismo reloj/volatilidad realizada). Nunca usar `Y_actual` para construir signo previo.
- Endpoint único `D = mean((S_hoy-S_previo)*Y_hoy)`. Puertas congeladas: mínimo 500 parejas, mínimo 150 señales por dirección, >=100 ISO semanas, 2000 bootstrap pareado por semanas `seed=941211`; `D>0`, límite inferior IC95 D>0 y retorno DRIVE bruto >0 para evidencia preliminar **no tradable**.
- Baseline mismo reloj no significa matching perfecto de volatilidad ex ante ni independencia de shocks. No se compara con RTH real CME; CFD broker `USTEC` puede tener horario y costes distintos.

## 3. Resultado científico real

| Métrica | Evidencia |
|---|---:|
| M1 provider-native auditadas | 3.486.929 |
| Formaciones NY completas con dirección no-cero | 2.549 |
| Faltantes 91/91 M1 en días nominales | 54 |
| Formación de retorno cero | 6 |
| Sin día causal anterior | 1 |
| Día anterior >5 días | 1 |
| **Jornadas apareadas** | **2.547** |
| DRIVE sentido alcista | 1.366 |
| DRIVE sentido bajista | 1.181 |
| Semanas ISO pareadas | 522 |
| Bootstrap válido | 2.000 / 2.000 |
| DRIVE retorno bruto medio | **+1.1195577002 bps** |
| STALE placebo retorno bruto medio | **+0.5329839463 bps** |
| **Delta primario** | **+0.5865737539 bps** |
| **IC95 delta** | **[−2.0514654078, +3.2517392863] bps** |
| Muestra mínima | PASS |
| Efecto bruto contra placebo | **FAIL, IC incluye cero** |

Desglose por año no promueve nuevos filtros: D positivo en 2016, 2019, 2020, 2021, 2023, 2024; D negativo en 2017, 2018, 2022, 2025 y 2026. Resultado inestable temporalmente, no seleccionar 2024 como modelo. Gran amplitud de IC frente al promedio bruto de ~1 bps.

## 4. Verificación de testigo independiente

El ZIP exacto del artifact #11719487773 fue extraído/inspeccionado independientemente:

- `drive-g1-out/drive-g1-nas100-report.json` SHA256 **`8f0679111fea0c4944656b036d180dd43aeaab73baa59ec052c854c6316abce1`**, coincide archivo `.sha256` y `OUTPUT_SHA256SUMS.txt`.
- `drive-g1-out/drive-g1-nas100-day-pairs.jsonl` SHA256 **`940760e6889d5c2c8711b729a99ef5f5809b603401847dc6d40d7c691cb0759f`**, coincide ambos testigos.
- 2.547 filas pares recontadas independientemente; 1.366 long / 1.181 short, **522 semanas**. Fórmulas de `gross_drive`, `gross_stale` comprobadas una por una desde `forward_bps` y signos; promedios y D recalculados desde JSONL coinciden EXACTAMENTE con reporte. Código ejecutado SHA coincide el manifest del artifact.
- Ninguna condición cambiada después del cálculo, no búsqueda de calendario/quantiles/activos para escoger una cifra favorable.

## 5. Dictamen

`DEV_DRIVE_GROSS_NO_SUPPORT` → **STOP de esta hipótesis exacta**. El resultado no cruza cero de forma robusta y su diferencial es pequeño, por lo que no está justificado pasar a estimaciones de fills/PF/Sharpe/Sortino/DD como si hubiera trader. Probar BID/ASK o coste no puede reparar la ausencia de señal bruta estadísticamente fiable, aunque sí importaría si alguna **hipótesis económica nueva** produce efecto robusto.

No afirmar que el modelo NAS100 de momentum en general no existe ni extrapolar al ETF QQQ, NQ CME o futuros; el proceso solo observó USTEC en CIBO. No proponer 09:15, 10:15, stops o ATR post-hoc para rescatar. Las pruebas sobre 10Y no son OOS independiente.

**Siguiente prioridad propuesta:** evaluar una hipótesis genuinamente distinta en RELATIVE (residual entre dos piernas, no momentum+otro reloj) con prerregistro primero, control de dos legs y volatilidad/exposición, y sin asegurar 3 traders. Antes de aplicar economía necesita verificar que los dos archivos M1 cTrader están sincronizados y el horizonte de hedge ratio es calculable solo con pasado. Seguir #794 y #789.

**Sin modificaciones a QORE producción, CIBO, Shared, QDLE, VPS, MT5 o LIVE. CERO TRADERS CERTIFICADOS por este trabajo.**
