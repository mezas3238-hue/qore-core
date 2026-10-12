# QORE Native G0 30/33 — CHFJPY source-only SHA audit ejecutada

**12 octubre 2026 UTC.** [PR #828](https://github.com/mezas3238-hue/qore-core/pull/828), [Actions exact-head #38205741712](https://github.com/mezas3238-hue/qore-core/actions/runs/38205741712) **3/3 SUCCESS**, código ejecutado `7c41bc4d0b135efb0885c17bafe9869342a5c377`. Auditorías: (1) contrato y pruebas, (2) 11 particiones originales de CHFJPY cTrader IC Markets DEMO con verificación RAW SHA, QUALITY SHA, manifiesto origen, identidad/UTC M5/recálculo velas, (3) unión a 29 originales inmutables con testigos SHA.

[Artefacto `qore-native-unified-30-m5.json` #11727276821](https://github.com/mezas3238-hue/qore-core/actions/runs/38205741712/artifacts/11727276821) más `OUTPUT_SHA256SUMS.txt` y code SHA. **SHA256 JSON del manifiesto 30** = `96b6709022905215d582abdc20edb452c7766dd42fd945e76144de8a29d29283`. Fuente primaria CHFJPY: captura IC Markets DEMO [#38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541) productor `e0ca5a13c866a19d8505c68cffc473598984b340`. Parent 29 congelado SHA `8ec07974e2276ab35f871064e03a6a0dedc87b987289b21cdcc737d599c447cb`.

| Grupo | Instrumentos fuente G0 | Velas M5 revalidadas |
|---|---:|---:|
| Parent original 29 | 29 | 21.396.360 |
| CHFJPY nuevo | 1 | 745.339 |
| **TOTAL** | **30/33** | **22.141.699** |

**G0 solo auditoría de HISTÓRICOS**, no 30 traders ni edge. Las doce series originales CIBO DEMO no se acreditaron como mismo broker/account que los 18 nuevos de IC Markets DEMO. No interpolación, cambio de hora, concatenación de símbolos o precios; M5 OHLC provider-relative no es BID/ASK ejecutable.

**Faltan tres históricos para G0 completo:** NZDJPY, NZDCAD, NZDCHF. Cuando terminen su captura en #38193802541, no confundir presencia de artefactos con 10Y original/RAW SHA auditado. Preparar un único suplemento congelado de estos tres basado en el manifiesto 30, con pruebas por mercado, y emitir manifest 33 SOLO si 3/3 pasan, **sin relanzar descargas**.

**Economía QORE Native:** se registran tres hipótesis prospectivas con NO_SUPPORT: H4 EURUSD persistencia #822, XAUUSD reversión #825, NAS100 NYC opening #827. El resultado NAS100 tuvo medias gross positivas ~2.46/2.85bps pero delta CI98.333 cruzó cero en ambos períodos; no constituye ventaja demostrada. No hacer barrido de 33 para rescatarlo. Faltan costos históricos BID/ASK, macro calendar known-as-of, broker H4/D1, riesgo real de stop y fill; ninguna certificación net. **0/3 traders certificados. Sin cambios VPS/MT5/CIBO/Shared/QDLE/LIVE.**
