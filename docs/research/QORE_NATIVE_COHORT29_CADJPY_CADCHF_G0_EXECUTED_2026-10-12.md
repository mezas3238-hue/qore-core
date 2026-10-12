# QORE Native 29/33 G0 — CADJPY y CADCHF verificados en GitHub

**12 octubre 2026 UTC. Trabajo finalizado, sin entrar a producción.** El manifiesto incremental de [PR #826](https://github.com/mezas3238-hue/qore-core/pull/826) añade exactamente CADJPY y CADCHF a los 27 M5 SHA-validos previos.

## Evidencia del resultado

- [Acción exact-head #38205083910](https://github.com/mezas3238-hue/qore-core/actions/runs/38205083910) **4/4 SUCCESS** (source contract, dos auditorías por símbolo, unión).
- Código probado: `c550e2f12195a018494a1c580c371dca21941a99`.
- [Artefacto fuente unificada #11727275974](https://github.com/mezas3238-hue/qore-core/actions/runs/38205083910/artifacts/11727275974): `qore-native-unified-29-m5.json`, `qore-native-unified-29-m5.json.sha256`, `OUTPUT_SHA256SUMS.txt`, `code-head-sha.txt`.
- SHA256 **del manifiesto JSON** comprobado: `8ec07974e2276ab35f871064e03a6a0dedc87b987289b21cdcc737d599c447cb` (no hash del ZIP).
- Parent 27 congelado: [#11726921285](https://github.com/mezas3238-hue/qore-core/actions/runs/38204152494/artifacts/11726921285), JSON SHA256 `499219430212dd50ffcefe681e6372ac3d66a54c420d03c3924d1ec2dc9680d0`, HEAD del código `56b07172bdded93f9fafadedf614c770a2a2dc40`.
- Productor nuevo IC Markets cTrader DEMO: [run #38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541), commit de fuente `e0ca5a13c866a19d8505c68cffc473598984b340`. Cada archivo extra fue verificado contra originales SHA `SOURCE_SHA256SUMS.txt`, `MANIFEST_SHA256SUMS.txt`, 11 particiones anuales raw+quality y timestamp cronológico UTC M5, sin leer OHLC de resultado.

| Grupo | Instrumentos | Barras M5 SHA-verificadas |
|---|---:|---:|
| Parent previo | 27 | 19.905.871 |
| CADJPY nuevo | 1 | 745.391 |
| CADCHF nuevo | 1 | 745.098 |
| **Unión lógica actual** | **29** | **21.396.360** |

**NO equivale a certificar 29 traders.** Son 29 **mercados/fuentes** G0 con históricos auditados. Los 12 originales CIBO DEMO no se han acreditado como misma cuenta IC Markets que los 17 nuevos. No se concatena una serie de instrumentos ni se presume BID/ASK, comisiones, sesiones H4/D1 broker ni cotización ejecutable. Sin histórico BID/ASK se permiten solo ensayos prospectivos OHLC brutales pre-registrados con costes RT **hipotéticos** y no certificación NET. No orders/PAPER/LIVE.

**Faltan cuatro para cupo 33:** CHFJPY, NZDJPY, NZDCAD y NZDCHF. En la última consulta del inicio de esta ronda, CHFJPY se descargaba y los otros tres se encontraban queued en el mismo run productor. Verificar estado real antes de ejecutar auditoría, no reactivar ni duplicar captura.

**Cierre de hipótesis H4:** EURUSD 12h persistence #822 y XAUUSD 12h reversal #825 dieron NO_SUPPORT con controles pareados y prereg previos al OHLC. No cambiar reglas a posteriori o probar 29 símbolos hasta encontrar un ganador. Nueva hipótesis diferente requiere prereg independiente, justificar cambio causal y multiplicidad. 0/3 traders Native certificados. Únicamente GitHub research, no cambios VPS/MT5/Shared/CIBO/QDLE.
