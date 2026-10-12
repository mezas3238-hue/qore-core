# QORE Native — Ejecutado G0 26/26: originales 23 + GBPNZD/AUDCAD/AUDCHF

**12 octubre 2026 UTC.** [PR #823](https://github.com/mezas3238-hue/qore-core/pull/823) investigación solamente. Integración lógica de 26 instrumentos con fuente, manifest SHA y RAW SHA anual separados, NO concatenación de cotizaciones de brokers/cuentas distintas. No señales ni PnL.

## Resultados reproducibles

**GitHub CI exact code SHA `2391063da42abdb733783ea9fb1781314419a946`**: [run #38203866777](https://github.com/mezas3238-hue/qore-core/actions/runs/38203866777), **5/5 SUCCESS** (1 source contract + 3 audits completos + 1 aggregate).

**Artefacto final**: [#11725589506](https://github.com/mezas3238-hue/qore-core/actions/runs/38203866777/artifacts/11725589506), contiene `qore-native-cohort26-unified.json`, SHA256 `da2b33c7be9e4bd56f561acd725b6777e68aa6ef9deee00b20c7a38cfb9ef862` y `OUTPUT_SHA256SUMS.txt`. Origen de los 23 congelado: manifest SHA256 `ca467b1d952420440b38d4e600606e43896e14230ac8438c7ceb4225a478770c`, código `cb9a21f77131b07db2da964ba123bd8c282ded23` en [run #38202227551](https://github.com/mezas3238-hue/qore-core/actions/runs/38202227551). Original 12 no perdidos ni reemplazados.

| Instrumento nuevo (source IC Markets DEMO #38193802541) | M5 nativo recontado | Particiones annual RAW/quality SHA |
|---|---:|---|
| GBPNZD | 745,203 | 11/11 PASS |
| AUDCAD | 745,423 | 11/11 PASS |
| AUDCHF | 745,393 | 11/11 PASS |
| **Total nuevo (3)** | **2,236,019** | **33 annual raw+quality SHA** |

**Total laboratorio 26: 19,160,586 barras originales M5**, frente a 16,924,567 en 23. Cada símbolo conserva identidad y fuente en manifest; no se usan OHLC ni retornos para escoger instrumentos.

**Interpretación G0:** `G0_26_OF_26_SOURCE_SHA_PASS_NO_ECONOMICS`; ningún coste broker BID/ASK acreditado, trading no autorizado, H4/D1 broker-native no certificado; origen 12 cTrader DEMO y nuevos 14 IC Markets DEMO no homologados como misma cuenta. Research bruto causal si futuro prereg lo autoriza, hipótesis H4-GROSS-01 EURUSD ya **NO_SUPPORT** ([PR #822](https://github.com/mezas3238-hue/qore-core/pull/822)) y no se puede rescatar pasando a 26 mercados.

**Fuente pendiente**: nueva captura #38193802541 sigue activa por tramos, con AUDNZD ya artefacto 15 de 21 al corte siguiente y cinco/seis no acabados. AUDNZD NO está admitido como G0 certificado aquí; auditarlo con mismos SHA antes de extender a 27. Política no-news #814 permanece intacta, 0/3 traders certificados. No VPS/MT5/CIBO/Shared/QDLE/LIVE ni merge producción.
