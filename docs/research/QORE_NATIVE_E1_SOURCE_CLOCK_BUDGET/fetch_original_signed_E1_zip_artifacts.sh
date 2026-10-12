#!/usr/bin/env bash
# Restore only EXISTING original GitHub E1 signed witness archives. No broker calls.
set -euo pipefail
: "${GH_TOKEN:?GitHub Actions artifact read token required}"
: "${QORE_E1_DATA_ROOT:?Source directory required}"
: "${QORE_E1_REPORT_DIR:?Report directory required}"
mkdir -p "$QORE_E1_DATA_ROOT"
while read -r symbol artifact original_sha; do
  case "$symbol" in
    EURUSD|GBPUSD|USDJPY|XAGUSD|SP500) file="qore-native-E1-seven-${symbol}-frozen-witness.zip";;
    *) file="qore-E1-${symbol}.zip";;
  esac
  curl --fail --silent --show-error --location --retry 2 \
    --header "Authorization: Bearer ${GH_TOKEN}" \
    --header 'Accept: application/vnd.github+json' \
    "https://api.github.com/repos/mezas3238-hue/qore-core/actions/artifacts/${artifact}/zip" \
    --output "${QORE_E1_DATA_ROOT}/${file}"
  printf '%s  %s\n' "${original_sha}" "${QORE_E1_DATA_ROOT}/${file}" | sha256sum --check --status
  printf 'SOURCE_SHA256_PASS %s\n' "${symbol}"
done < "${QORE_E1_REPORT_DIR}/artifact_register.txt"
