# QORE Native H4-GROSS-02 XAUUSD — Ejecutado NO_SUPPORT (sin rescates post hoc)

**Fecha 2026-10-12 UTC**. Segunda hipótesis distinta (reversión de metal). Prereg [commit SHA 94bc58e89b5b2112e1c65df77a077bff2758b63c](https://github.com/mezas3238-hue/qore-core/commit/94bc58e89b5b2112e1c65df77a077bff2758b63c) fue anterior a resultados; Actions [#38204480486](https://github.com/mezas3238-hue/qore-core/actions/runs/38204480486) exact-head `70c4a6e7b77b05057cb74508a4d437d12d2f81c2` 2/2 jobs SUCCESS. Artefacto original [#11726632551](https://github.com/mezas3238-hue/qore-core/actions/runs/38204480486/artifacts/11726632551) incluye JSON, SHA y code head. [PR #825](https://github.com/mezas3238-hue/qore-core/pull/825).

| Métrica | Desarrollo 2016-09-17→2022-09-17 | Diagnóstico 2022-09-17→2024-09-17 |
|---|---:|---:|
| n eventos-día | 1,480 | 495 |
| ISO semanas bootstrap | 313 | 105 |
| Gross signed mean XAUUSD 12h contrarian bps | −0.228292 | −1.665567 |
| Baseline 4h contrarian mean bps | +0.207853 | −1.553410 |
| Paired delta bps | −0.436145 | −0.112157 |
| IC 97.5% delta, semana bootstrap 2000 semilla 20261012 | [−2.216163, +1.314571] | [−3.011690, +2.744390] |
| IC 97.5% estrategia gross | [−2.323119, +1.939266] | [−5.667346, +2.146473] |
| Long/short | 727 / 753 | 241 / 254 |
| Gross positividad | 49.9324% | 48.6869% |
| Resultado con escenario hipotético RT 1bps | −1.228292 | −2.665567 |
| **Dictamen prereg** | **NO_SUPPORT** | **NO_SUPPORT** |

2,063 días UTC potenciales, 1,975 observaciones aptas, 88 excluidos por bloques M5 H4 calendar-UTC incompletos. 565,955 velas M5 en plazo; OHLC 2024-09-17 en adelante NO leído por contrato; fuentes originales XAUUSD cTrader DEMO con 11 years RAW SHA validados independientemente antes de extraer campos OHLC. Solo UNA clase/símbolo en esta ronda; no 27 mercados y selección por PnL.

**Lectura:** en ambos tramos la media gross ya es negativa, el delta pareado es negativo y los intervalos CI97.5% incluyen 0. Ningún parámetro se movió para salvar resultados. NO_SUPPORT significa que esta regla congelada no exhibió ventaja bruta demostrada, NO que ninguna reversión de oro pueda funcionar. A 0 coste teórico gross el promedio ya es negativo; el break-even medio en términos de coste no-negativo no existe. Los costes 0,1,3,5,10,20bps son escenarios, no BID/ASK real.

**Multiplicidad/seguridad:** H4-GROSS-01 EURUSD [PR #822](https://github.com/mezas3238-hue/qore-core/pull/822) también NO_SUPPORT. Esta hipótesis usó alfa .025 e IC97.5%, pero ello no corrige retroactivamente todas las pruebas históricas Core/RESET/DRIVE. No existe calendario macro conocido as-of, spreads broker, fill, stop o financiación; este estudio es GROSS_NEWS_UNFILTERED (no trader operable Native no-news). El periodo 2024-2026 OHLC continúa embargado. 0/3 traders certificados, sin VPS/MT5/CIBO/Shared/QDLE/LIVE.

**Decisión de programa:** cerrar ambas hipótesis sin retuning. No ampliar inmediatamente a 27×variantes buscando el ganador. Continuar G0 restante y consolidar un nuevo mecanismo económico diferenciado (con magnitud esperada y potencia, límites de costes estimados y calendario causal), prereg previamente. Si faltan fuentes para identificarlo, declarar SOURCE_BLOCKED y no inventar PF/Sharpe netos.