#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
  # --model-dir=data/ \
akaza-data check \
  --model-dir=/usr/share/akaza/model/default \
  --eucjp-dict=skk-dev-dict/SKK-JISYO.L \
  --utf8-dict=data/SKK-JISYO.akaza \
  "$@"
akaza-data check \
  --model-dir=data/ \
  --eucjp-dict=skk-dev-dict/SKK-JISYO.L \
  --utf8-dict=data/SKK-JISYO.akaza \
  "$@"
