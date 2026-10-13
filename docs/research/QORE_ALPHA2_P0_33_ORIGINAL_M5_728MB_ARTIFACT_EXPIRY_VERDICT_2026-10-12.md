# QORE-Alpha 2 — P0 Archivo original 33 M5; censo real de vencimientos SHA (2026-10-12)

## Resultado GitHub verificable — solo metadata, sin abrir una sola vela

- Prerregistro `docs/research/QORE_ALPHA2_P0_SOURCE33_ARTIFACT_EXPIRATION_ARCHIVE_READINESS_PREREG_2026-10-12.md`, commit ancestro `cc566b60eaea12d29cedff1314989ff9b4b586c8`, antes de consultar API de artefactos programáticamente.
- Auditor propio: `src/qore/research/alpha2_source33_artifact_expiry_inventory.py` + pruebas negativas `tests/research/test_alpha2_source33_artifact_expiry_inventory.py`. [GitHub Actions #38302743314](https://github.com/mezas3238-hue/qore-core/actions/runs/38302743314), exact HEAD `7e5279eb07a09275a452fc3f57aaf87d75dc1f77`, **SUCCESS 7/7 tests + Ruff**, reporte firmado metadata-only artifact **#11771227114**, ZIP digest `sha256:5f0aef77dafaa9895993213a88603ec768c6a51422db8051d774a474fd8d8926`.
- Comprueba tres runs originales **SUCCESS**, con SHA del código exacto y sin descargar ZIP: Atlas original12 [#35166210458](https://github.com/mezas3238-hue/qore-core/actions/runs/35166210458) HEAD `ab782b8e9f890f86a2b6500070f0556b4b685e3d`; nuevo21 [#38193802541](https://github.com/mezas3238-hue/qore-core/actions/runs/38193802541) HEAD `e0ca5a13c866a19d8505c68cffc473598984b340`; manifiesto33 firmado [#38207337960](https://github.com/mezas3238-hue/qore-core/actions/runs/38207337960) HEAD `dba0e0c3b61e430d3ed51abab562ebd92060a0ff`.
- **33/33 archivos M5 originales presentes**: 12 Atlas +21 nuevo; se confirma además el agregado original Atlas 12 y la existencia del manifiesto final 33. Todos reportan `expired=false`, ID de artefacto distinto, `digest=sha256:<64hex>`, bytes de archivo y fecha de expiración exacta desde REST; no se copiaron datos de precios, ni se fingió que estos hashes prueban restauración.

| Cohorte original | Archivos M5 | Tamaño ZIP | Vencimiento GitHub Actions |
|---|---:|---:|---|
| Atlas CIBO original | 12 | ~260 MB | **2026-12-16 00:21:18 UTC** |
| ICMarkets nueva | 21 | ~468 MB | **2027-01-10 aprox.** |
| **TOTAL M5** | **33** | **728.048 MB** | **Primer vencimiento 2026-12-16** |

En la medición exacta de CI restaban **64.172 días** al primer vencimiento. Estado firmado: `P0_ARCHIVE_VAULT_LICENSE_AND_RESTORE_BEFORE_EXPIRY`. Hoy son artefactos **TEMPORALES**, NO `SOURCE_ARCHIVED_PERMANENTLY`.

## Acciones para el owner #837 — orden de ejecución

1. **Inmediatamente** revisar derecho contractual/licencia de conservación y redistribución de históricos broker/cTrader y aprobar repositorio privado de acceso limitado, coste, cifrado, versionado y retención. Jamás subir 728 MB brutos al Git público ni a GitHub Releases públicos; no crear bucket de pago sin autorización.
2. Hacer **backup físico exacto de los originales 12 Atlas antes del 2026-12-16 00:21:18 UTC**. Cada original deberá conservar ID de GitHub, ZIP SHA256 oficial, manifest interno de SHA por archivo/año, símbolos, lote, proveedor y timestamps de extracción. Desacoplar de la nueva cohorte de 21 con distintas credenciales DEMO.
3. Exportar luego los 21 nuevos antes de **2027-01-10** y el manifest de 33; incorporar M1 cuando sea verificado. Comprobar espacio necesario con margen, cuota, las 33+ fuentes y licencias; la suma de 728 MB mide ZIP originales M5, **no** el tamaño de descompresión ni redundancia/replicación/M1.
4. Un auditor distinto deberá restaurar muestras anuales en otro entorno aislado, recalcular SHA SHA internos antes de decodificar, comprobar 33/33 períodos y símbolos originales y dar `SOURCE_ARCHIVED_PERMANENTLY` solo tras **restore real**.
5. Conservar estado de holdout: no describir después de backup como holdout virgen. Estos originales 2016–2024 ya fueron usados para investigación. El backup es de disponibilidad, no de ventaja estadística.

## Frontera inalterada

Códigos y QA de G2 BIDASK 29 MARKET vs 4 broker source P0 quedan en la rama de investigación; live Broker `SymbolById` falló en V1/V2/V3 (no insistir), evidencia previa USTEC source SHA PASS pero NAS100 contrato histórico sigue NO probado. W1 PATR W2 PADE W3 CMTRL siguen SIN SOPORTE GROSS y sin certificación. No NET, no Sharpe/Sortino/DD NET, no órdenes, nada de VPS/MT5/CIBO/Shared/QDLE/LIVE/MAIN.

**Responsable de licencia/vault**: issue [#837](https://github.com/mezas3238-hue/qore-core/issues/837). Responsable económicos de Alpha2 [#852](https://github.com/mezas3238-hue/qore-core/issues/852), contratos [#868](https://github.com/mezas3238-hue/qore-core/issues/868). El GitHub Actions original es un lugar temporal, no un vault duradero.
