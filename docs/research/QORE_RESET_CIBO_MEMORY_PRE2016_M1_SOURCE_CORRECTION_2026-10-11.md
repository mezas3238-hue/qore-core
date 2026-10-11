# Corrección de memoria CIBO: el archivo de EURUSD comienza en 2014, no 2016

**2026-10-11.** Informe de procedencia documental y metadatos **sin abrir OHLC del holdout sellado**. Directiva del usuario: consultar la memoria de CIBO antes de pedir descargas nuevas. **No sustituye ticks BID/ASK por velas M1.**

## Evidencia pública en GitHub Actions ya completada

- Fuente [run #36367221571](https://github.com/mezas3238-hue/qore-core/actions/runs/36367221571), **SUCCESS de 21/21 jobs**, SHA `660881acc008593eb04b7be2c4e2e60f06950a4d`, workflow `.github/workflows/qore-capitalizer-pre2016-sealed-holdout-v1.yml`.
- Documento sellado por metadatos original [artifact #10947804689](https://github.com/mezas3238-hue/qore-core/actions/runs/36367221571/artifacts/10947804689), `pre2016-sealed-holdout-freeze.json`: `lookback_start=2014-08-27T00:00:00Z`; `holdout_start=2014-09-17T00:00:00Z`; `holdout_end_exclusive=2016-09-17T00:00:00Z`. `selection_basis=TIMESTAMP_COVERAGE_ONLY_NO_ECONOMICS`, `economics_seen=false`, `holdout_may_tune_candidate=false`.
- Inventario del programa original [artifact #10948728912](https://github.com/mezas3238-hue/qore-core/actions/runs/36367221571/artifacts/10948728912), `pre2016-sealed-m1-inventory.json`: **EURUSD 762.455 velas M1 nativas**, `provider_native_m1=true`, total `target_start=2014-08-27T00:00:00Z` → `target_end_exclusive=2016-09-17T00:00:00Z`, `holdout_economics_evaluated=false` según manifiesto de esa ejecución. La descarga bruta original está conservada como [artifact EURUSD #10948342218](https://github.com/mezas3238-hue/qore-core/actions/runs/36367221571/artifacts/10948342218), vigente en el momento de esta auditoría.
- El censo original EURUSD [artifact #10948630676](https://github.com/mezas3238-hue/qore-core/actions/runs/36367221571/artifacts/10948630676), `eurusd-pre2016-availability.json`, declara `all_requested_months_have_provider_data=true`; esto no debe exagerarse a cada minuto completo ni ticks reales.
- Otros 8 M1 nativos en el mismo manifiesto: AUDJPY 766.041, AUDUSD 762.174, GBPJPY 766.014, GBPUSD 762.547, NAS100 684.125, USDCAD 756.919, USDJPY 764.292, XAUUSD 719.090; todos 2014-08 a 2016-09. No son nueve mercados M1 por diez años.

## Lo que realmente cambia para RESET

1. **Sí existe EURUSD de 2015 en la memoria de CIBO** — desde **2014-08-27**. Era incorrecto limitar toda la memoria CIBO a Atlas 10Y M5 `2016-09..2026-09`. Este último conjunto es distinto, no elimina las fuentes pre-2016.
2. La fuente encontrada es **provider-native M1** (velas), **NO tick BID/ASK**. No puede utilizarse como prueba de orden intraminuto, spread ni libro de cotizaciones originales. No se han leído OHLC, hecho backtest, ni consumido su holdout sellado en esta auditoría.
3. **La PR #803** de descarga de ticks cTrader continúa bloqueada por `ProtoOAGetAccountListByAccessTokenReq`, como mostró [CI #38177511169](https://github.com/mezas3238-hue/qore-core/actions/runs/38177511169). El hallazgo de este archivo M1 **no repara credenciales** ni acredita ticks desde 2015.
4. Se debe **priorizar reuse de cTrader CIBO M1** para estudios que solo requieran M1 cuando sus reglas de reserva/holdout permitan abrirlos; **no pedir re-descarga M1** si ya hay artifact. Para estudiar RESET G2 con ticks originales, el gate sigue siendo autorización de cTrader más descarga independiente de BID y ASK, sin fuentes externas ni M1 sintético.

**Decisión:** `CIBO_PRE2016_NATIVE_M1_ARCHIVE_VERIFIED`; `RESET_G2_CTRADER_TICK_SOURCE_NOT_VERIFIED`; `SEALED_HOLDOUT_UNTOUCHED`; no producción/VPS/MT5.
