# VT31 — prereg certificación método/cognitiva con 10 artifacts inmutables + TraderLab

Fecha 2026-10-15, ANTES del código. El usuario pide rapidez usando Trader Lab Ultra Fast Runner, pero VT31 se certifica por metodología y cognitiva, no por PF/DD/Sharpe.

Se preserva el tribunal original `scripts/vt31_qualitative_method_cog_certificate_decision_20261015.py` (8 expedientes fuente, salida METODOLOGIA PENDIENTE y COGNITIVA PENDIENTE mientras falten doctrina y firmas reales). Nuevo verificador EXTERNO añadirá dos ARTIFACTS cualitativos verificables sin alterar ni relajar ninguna condición original:

1. #965 artifact `11976412423`, ZIP SHA256 `e52de6f442238be555eb739d8d46082cb83a2132f49e6bcf3d748de462d3fd4e` y `VT31_G3_TRADERLAB_NATIVE_32X_QUALITATIVE_PARITY.json`: 12 casos SHORT/WAIT 1× vs 32×, COG G3 SHA intacto, calendario nativo, no L3 real.
2. #967 artifact `11979797382`, ZIP SHA256 `a77be5d7c66a767a4f0724f2b981571f3972fc0eee992a2b9b2ea70c7ccad25b` y `VT31_TRADERLAB_NATIVE_32X_G3_COG_BIDIRECTIONAL_24_CASES.json`: 24 LONG+SHORT/WAIT 3 ventanas EST/EDT, mismos M1/timestamps/DOL/razones/trazas con 1× y 32×, no L3 real.

Condición ex ante: el verificador nuevo descarga diez ZIP (los ocho del tribunal #964 + estos dos), valida HASH SHA256 de cada ZIP y SHA256SUMS de sus contenidos; consulta reviews reales #896 y issue #897; llama al dictamen original de 8 dimensiones, comprueba 12+24 tipos y SHA G3 inmutable, añade UN NUEVO flag POSITIVO `COG_original_1x_32x_native_lab_semantic_parity` y `COG_bidirectional_DST_source_behavior`, **sin** crear certificado por ese flag. Si algún SHA, caso o flag de certificado falsificado cambia => FAIL CLOSED. Autoridad humana no puede sustituirse con CI.

CI pytest paralelo cuando aplique; GitHub Actions pipeline real; no nueva búsqueda 3Y, no fondos, no sizing/OMS/LIVE, no CPU 32× probado. Mantener original G3 COG/OPS/acta sin modificaciones. Se producen JSON/manifest y handoff técnico. Prueba los casos antiguos como regresión, no simula nombres de revisores.

Salida esperada: 10 artifacts inmutables, 12 SHORT y 24 bidireccionales, todos paridad TRUE, metodología/cognitiva `PENDIENTE` por doctrina y dos firmas #897, no PnL. Cualquier desviación se documenta, sin cambiar expectativas ex post.