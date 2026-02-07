#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
akaza-data check \
  --model-dir=data/ \
  --eucjp-dict=skk-dev-dict/SKK-JISYO.L \
  --utf8-dict=data/SKK-JISYO.akaza \
  "$@"
