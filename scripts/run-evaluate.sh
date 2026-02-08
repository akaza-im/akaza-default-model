#!/bin/bash
# 評価実行 + 結果保存スクリプト
# Usage: scripts/run-evaluate.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP="$(date '+%Y%m%d%H%M')"
OUTDIR="tmp/evaluate/$TIMESTAMP"
HISTORY="tmp/evaluate/HISTORY.tsv"

mkdir -p "$OUTDIR"

# 評価実行
echo "Running make evaluate..."
make evaluate 2>&1 | tee "$OUTDIR/raw.txt"

# BAD 行抽出
grep '^\[BAD\]' "$OUTDIR/raw.txt" > "$OUTDIR/bad.txt" || true

# TOP-5 行抽出
grep '^\[TOP-5\]' "$OUTDIR/raw.txt" > "$OUTDIR/top5.txt" || true

# パターン分析
python3 scripts/extract-patterns.py < "$OUTDIR/raw.txt" > "$OUTDIR/patterns.txt" 2>&1 || true

# スコア抽出 (最終行: "Good=5962, Top-5=473, Bad=4630, elapsed=183403ms, 再現率=91.646194")
SUMMARY_LINE=$(grep 'Good=[0-9].*再現率=' "$OUTDIR/raw.txt" | tail -1)
GOOD=$(echo "$SUMMARY_LINE" | grep -oP 'Good=\K[0-9]+' || echo "0")
TOP5=$(echo "$SUMMARY_LINE" | grep -oP 'Top-5=\K[0-9]+' || echo "0")
BAD=$(echo "$SUMMARY_LINE" | grep -oP 'Bad=\K[0-9]+' || echo "0")
RECALL=$(echo "$SUMMARY_LINE" | grep -oP '再現率=\K[0-9.]+' || echo "N/A")

COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
DATE=$(date '+%Y-%m-%d %H:%M')

# サマリー保存
cat > "$OUTDIR/summary.txt" <<EOF
Date: $DATE
Commit: $COMMIT
Good: $GOOD
Top-5: $TOP5
Bad: $BAD
Recall: $RECALL
EOF

# HISTORY.tsv に追記 (ヘッダーがなければ作成)
if [ ! -f "$HISTORY" ]; then
    printf "datetime\tcommit\tgood\ttop5\tbad\trecall\n" > "$HISTORY"
fi
printf "%s\t%s\t%s\t%s\t%s\t%s\n" "$DATE" "$COMMIT" "$GOOD" "$TOP5" "$BAD" "$RECALL" >> "$HISTORY"

# サマリー表示
echo ""
echo "=========================================="
echo "  Evaluation Summary"
echo "=========================================="
echo "  Date:    $DATE"
echo "  Commit:  $COMMIT"
echo "  Good:    $GOOD"
echo "  Top-5:   $TOP5"
echo "  Bad:     $BAD"
echo "  Recall:  $RECALL"
echo "=========================================="
echo "  Results saved to: $OUTDIR/"
echo "=========================================="
