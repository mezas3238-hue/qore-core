# QORE Native — Fuente 33 — recheck auditable #1 (2026-10-12)

Este archivo activa exclusivamente el workflow GitHub Research `.github/workflows/qore-native-final33-m5-g0.yml` para revisar nuevos artefactos originales de la captura #38193802541.

Al crear este trigger se verificaron los originales de **NZDJPY** y **NZDCAD** presentes en el catálogo; **NZDCHF todavía IN_PROGRESS**, sin archivo disponible. El testigo NZDJPY ya había pasado en run #38206111777 (745.313 M5), pero una nueva ejecución SHA contra originales no reutiliza hashes como sustituto de RAW.

**Contrato obligatorio:** auditar individualmente cualquier símbolo descargado, pero nunca publicar `G0_33_OF_33` hasta los tres últimos originales validos en MISMA ejecución. No descargar duplicados, no PnL, no OHLC de resultados, ningún VPS/MT5/LIVE. 30 consolidados, 1 verificado aparte, tercero pendiente; los 33 no están todavía completos.

## Ejecución FINAL de las 21 descargas publicadas

El artifact fuente NZDCHF `11727882491` figura ahora en la captura original GitHub Actions #38193802541. Con NZDJPY y NZDCAD, son 21/21 nuevos públicos. Este trigger activa **una auditoría fresca de las 3 fuentes originales** y publicación 33 únicamente si todos pasan el mismo run; incluye censo estructural de 33, no señales ni PnL. La existencia de artifact no constituye la validación SHA. Las 12 fuentes originales y 30 anteriores permanecen congeladas.
