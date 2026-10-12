# QORE Native H4-GROSS-01 EURUSD — Ejecutado y cerrado: NO_SUPPORT

Fecha UTC 2026-10-12. Diseño preregistrado ANTES de consultar OHLC: commit a4424ba3027018bab54f03aff668894f63f47da9. [PR #822](https://github.com/mezas3238-hue/qore-core/pull/822), [GitHub Actions #38203530559](https://github.com/mezas3238-hue/qore-core/actions/runs/38203530559), exact-head fe73b6c04f582c2eac6549b97530ff8c45d32576, 2/2 jobs SUCCESS, [artefacto original #11725134876](https://github.com/mezas3238-hue/qore-core/actions/runs/38203530559/artifacts/11725134876) con JSON, sha y code head.

| Métrica | Desarrollo 2016-09-17→2022-09-17 | Diagnóstico 2022-09-17→2024-09-17 |
|---|---:|---:|
| Días n | 1,526 | 510 |
| Semanas bootstrap | 313 | 105 |
| Media signed gross estrategia bps | +0.355302 | +0.746371 |
| Media baseline signo últimas 4h bps | −0.388108 | +1.004264 |
| Delta pareado bps | +0.743410 | −0.257893 |
| IC95 delta bootstrap por semana (2,000 seed 20261012) | [−0.142367, +1.645114] | [−1.715618, +1.221282] |
| IC95 media gross | [−0.552368, +1.248603] | [−0.963864, +2.455488] |
| Long/short | 731 / 795 | 249 / 261 |
| Proporción gross positiva | 49.4758% | 52.5490% |
| Break-even media coste RT hipotético bps | 0.355302 | 0.746371 |
| Media tras escenario RT =1bps | −0.644698 | −0.253629 |
| Veredicto pre-registrado | NO_SUPPORT | NO_SUPPORT |

Total observado: 2,073 días UTC con M5 en marco de investigación, 2,036 elegibles, 37 días excluidos por bloques incompletos; 596,349 barras M5 revisadas en plazo. Únicamente EURUSD en 23 mercados, SIN mirar otros precios; 2024-09-17 en adelante OHLC no leído y continúa reservado. El control y la estrategia comparados en exactamente las mismas fechas.

**Interpretación:** ambos IC95 del delta incluyen cero, la diferencia pareada se torna negativa en el diagnóstico, IC95 de media gross incluye cero. Se cumplieron los umbrales mínimos de conteo preregistrados (300 días y 52 semanas por período) pero NO el de ventaja reproducida y límite inferior positivo. CERRAR ESTA REGLA, no mover horarios, mercado o stops para rescatar el resultado. NO demuestra ausencia general de edge ni que un edge positivo fue eliminado por costes.

**Costes:** los escenarios 0, 1, 3, 5, 10, 20 bps RT NO son BID/ASK broker; RT=0 es únicamente gross matemático, no 'neto sin coste'. No hubo stop, fill, spread broker, calendario de noticias PIT ni certificación de ejecución. Los ingresos medios positivos brutos no son una estrategia neta certificable. Alta incertidumbre no-news; el run es GROSS_PHENOMENON_ONLY_NEWS_UNFILTERED y no modifica la política #814.

**Estado del programa:** 0/3 traders certificados. No tocar VPS, MT5, LIVE, CIBO, Shared ni QDLE. Mantener falsación registrada. Ampliación 23→26 como auditoría G0 por separado no cambia el veredicto de H4-GROSS-01.