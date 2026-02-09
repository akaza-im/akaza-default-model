#!/usr/bin/env python3
"""分類 TSV のサマリーを表示する。

Usage:
    python3 scripts/classify-summary.py CLASSIFICATION.tsv
"""

import sys


def main():
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} CLASSIFICATION.tsv', file=sys.stderr)
        sys.exit(1)

    categories = {}
    total = 0
    with open(sys.argv[1]) as f:
        header = f.readline()
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 4:
                continue
            total += 1
            cat = parts[3]
            categories[cat] = categories.get(cat, 0) + 1

    print(f'=== Classification Summary ({total} entries) ===')
    print()
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total else 0
        print(f'  {cat:30s} {count:4d}  ({pct:.1f}%)')
    print()


if __name__ == '__main__':
    main()
