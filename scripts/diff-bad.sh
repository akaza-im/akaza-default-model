#!/bin/bash
# 2つの evaluate 結果の BAD リストを比較する
# 使い方:
#   scripts/diff-bad.sh <old_dir> <new_dir>
#   scripts/diff-bad.sh  # 引数なしで最新2つを比較
#
# 出力:
#   改善(removed from BAD)と退行(added to BAD)の件数とリスト

set -euo pipefail

EVAL_DIR="tmp/evaluate"

if [ $# -eq 2 ]; then
    OLD="$1"
    NEW="$2"
elif [ $# -eq 0 ]; then
    # 最新2つのディレクトリを自動選択
    dirs=($(ls -d "$EVAL_DIR"/2* 2>/dev/null | sort | tail -2))
    if [ ${#dirs[@]} -lt 2 ]; then
        echo "ERROR: 比較するには2つ以上の evaluate 結果が必要です" >&2
        exit 1
    fi
    OLD="${dirs[0]}"
    NEW="${dirs[1]}"
else
    echo "Usage: $0 [old_dir new_dir]" >&2
    exit 1
fi

OLD_BAD="$OLD/bad.txt"
NEW_BAD="$NEW/bad.txt"

if [ ! -f "$OLD_BAD" ] || [ ! -f "$NEW_BAD" ]; then
    echo "ERROR: bad.txt が見つかりません" >&2
    echo "  OLD: $OLD_BAD" >&2
    echo "  NEW: $NEW_BAD" >&2
    exit 1
fi

echo "=== Comparing ==="
echo "  OLD: $OLD"
echo "  NEW: $NEW"
echo ""

improved=$(diff <(grep '^\[BAD\]' "$OLD_BAD" | sort) <(grep '^\[BAD\]' "$NEW_BAD" | sort) | grep '^<' | wc -l || true)
regressed=$(diff <(grep '^\[BAD\]' "$OLD_BAD" | sort) <(grep '^\[BAD\]' "$NEW_BAD" | sort) | grep '^>' | wc -l || true)

echo "  Improved (removed from BAD): $improved"
echo "  Regressed (added to BAD):    $regressed"
echo "  Net change:                   -$((improved - regressed))"
echo ""

if [ "$regressed" -gt 0 ]; then
    echo "=== Regressions ==="
    diff <(grep '^\[BAD\]' "$OLD_BAD" | sort) <(grep '^\[BAD\]' "$NEW_BAD" | sort) | grep '^>' | sed 's/^> //' || true
    echo ""
fi

if [ "$improved" -gt 0 ]; then
    echo "=== Improvements ==="
    diff <(grep '^\[BAD\]' "$OLD_BAD" | sort) <(grep '^\[BAD\]' "$NEW_BAD" | sort) | grep '^<' | sed 's/^< //' || true
fi
