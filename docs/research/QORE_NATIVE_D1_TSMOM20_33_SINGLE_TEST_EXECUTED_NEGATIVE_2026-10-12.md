# QORE Native — RESULTADO EJECUTADO: una prueba D1 TSMOM-20, 33 mercados

**Fecha 2026-10-12. Resultado observado después del preregistro.** [PR #877](https://github.com/mezas3238-hue/qore-core/pull/877) · [GitHub Actions #38316660915](https://github.com/mezas3238-hue/qore-core/actions/runs/38316660915) **SUCCESS 2/2 jobs** · commit de código realmente evaluado **`890252a9bae1f1f5892b6fa92da1de8d1054f136`**. Diez pruebas unitarias sintéticas PASS.

**Regla preregistrada antes de abrir resultados:** [especificación TSMOM](QORE_NATIVE_D1_TSMOM20_33_SINGLE_TEST_PREREG_2026-10-12.md). 33 instrumentos G0 sin selección, dirección del retorno de los últimos 20 días de negociación completados, precio de entrada proxy apertura M5 de próxima fecha UTC a partir de 00:10, como mínimo cinco minutos después de cierre previo, salida/reevaluación en próximo proxy open. Un bp asumido por lado, pesos fijos 1/33, periodos analizados 2016-2021 DEV y 2022-2024-09-16 DIAG, 252 días hábiles anualización. Cero búsqueda de 10/40/60 señales, cero backtest del tramo protegido a partir de 2024-09-17.

## Resultados económicos (retorno con coste SUPUESTO, no NET real)

| Métrica | DEV 2016-09-17 a 2021-12-31 | DIAG 2022-01-01 a 2024-09-16 |
|---|---:|---:|
| Sharpe 252, Rf=0 | **-0.09199437373590758** | **-0.272045350834798** |
| Retorno geométrico anualizado 252 | **-0.004576190154397031** | **-0.012591915228691408** |
| Max Drawdown | **-0.11961191106420221** | **-0.07190843839714633** |
| Posiciones mercado-día | 44696 | 23248 |
| Correlación con SP500 **CFD**, no SPX | -0.173491382520997 | -0.14895765710234485 |

La prueba dio **Sharpe negativo en ambos tramos**. Conforme al preregistro, `DIAG Sharpe <= 0` implica **rechazar esta especificación TSMOM-20 del panel** como hipótesis de edge, **no retunearla con DIAG ni mirar holdout 2024-2026 para rescatarla**. El resultado no demuestra que toda estrategia de momentum diario sea inviable ni que cada mercado carezca de edge, únicamente que esta regla fija no tiene soporte positivo en este estudio.

## Integridad, alcance y artefacto

- [Ejecución Actions #38316660915](https://github.com/mezas3238-hue/qore-core/actions/runs/38316660915): job `synthetic_unit` PASS; job `single_frozen_historical_panel` PASS. 33 mercados `TSMOM_D1_MARKET_PASS`, 33 sets de 11 particiones anuales M5 fuente/manifest/verificación RAW SHA original, sin consultas al broker.
- Artefacto [#11777736126](https://github.com/mezas3238-hue/qore-core/actions/runs/38316660915/artifacts/11777736126); digest ZIP de Actions **`sha256:f67ce9dd761084c12b3f0a2680055beb9fe5eb1c656b779ab43ff6f0925dce56`**. Expira el **2026-11-11T22:32:03Z** (Actions, no vault permanente). Contiene el JSON con métricas por cada uno de 33 símbolos y por periodo, el SHA de código y SUMS; **no contiene históricos raw M5 ni cotizaciones BID/ASK**.
- Fuentes originales: Atlas CIBO doce mercado-run #35166210458; nuevas 21 IC Markets run #38193802541. La igualdad económica de contratos no está demostrada.
- El procesamiento no calculó outcomes de barras con fecha `>=2024-09-17`; sí verificó integridad SHA de las particiones para proteger la procedencia y mantener cohorte original.
- Correlación solo con el **SP500 CFD** de la propia fuente; no se consultó SPX cash. El Sharpe del panel no son 33 observaciones independientes por su correlación entre FX/crosses.
- **Limitaciones económicas:** 1 bp lado optimista, `OPEN` de barra proxy no fill, 0 financiación real ni swaps, no comisión broker histórica, no control noticias PIT, calendario diario UTC que no equivale necesariamente a D1 broker, original12 y nuevo21 no homologados. Por tanto, `G1_NET_BLOCKED` y `CERTIFIED_TRADERS_0_OF_3`.

## Decisión metodológica y siguiente investigación (NO acciones añadidas)

1. **Cerrar hipótesis TSMOM-20 como `NO_POSITIVE_SUPPORT_IN_DEV_OR_DIAG`** y no optimizar parámetros a posteriori. Si surgiera una hipótesis genuinamente diferente debe justificarse y congelarse antes de mirar resultados, con tiempo/horizonte de nuevo holdout válido.
2. No escalar la reconstrucción masiva de 373.611 operaciones E1 solo por infraestructura. Priorización ahora basada en evaluación económica falsable.
3. Mantener abierto #837 vault/licencia y la custodia de las fuentes por ser independiente de qué estrategia gane; #857 #856 #863 no autorizan NET y no deben consumirse para rescatar este TSMOM.
4. El plan propietario de 3 traders QORE Native persiste como objetivo, pero hoy **0/3** demostrados/certificados, sin edge replicado.

**Resultado final resumido:** D1 TSMOM20 33/33 fuentes PASS; DEV Sharpe -0,092; DIAG Sharpe -0,272; edge NO_SUPPORT; broker NET NO DEMOSTRADO; sin producción, holdout intacto.
