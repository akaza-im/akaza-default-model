#!/usr/bin/env python3
"""evaluate の bad.txt をフィルタリングして真の BAD 件数を算出する。

Usage:
    python3 scripts/filter-evaluate.py [evaluate_dir]
    python3 scripts/filter-evaluate.py  # 引数なしで最新を使用

evaluate-filter/accept.tsv と evaluate-filter/ignore.txt を読み込み、
bad.txt からスタイル差や曖昧なエントリを除外した結果を表示する。

注意: Recall(再現率) は文節レベルで計算されるため、文単位のフィルタリングでは
正確な Adjusted Recall を出せない。BAD 件数の変化で比較すること。
"""

import os
import re
import sys


def load_accept(path):
    """accept.tsv を読み込む。{reading: {akaza_output, ...}} を返す。"""
    accept = {}
    if not os.path.exists(path):
        return accept
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                reading, akaza = parts[0], parts[1]
                accept.setdefault(reading, set()).add(akaza)
    return accept


def load_ignore(path):
    """ignore.txt を読み込む。{reading, ...} を返す。"""
    ignore = set()
    if not os.path.exists(path):
        return ignore
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            ignore.add(parts[0])
    return ignore


def find_latest_evaluate_dir(base_dir='tmp/evaluate'):
    dirs = []
    for d in os.listdir(base_dir):
        full = os.path.join(base_dir, d)
        if os.path.isdir(full) and d.startswith('2'):
            dirs.append(full)
    if not dirs:
        print('ERROR: evaluate ディレクトリが見つかりません', file=sys.stderr)
        sys.exit(1)
    return sorted(dirs)[-1]


def main():
    if len(sys.argv) >= 2:
        eval_dir = sys.argv[1]
    else:
        eval_dir = find_latest_evaluate_dir()

    bad_file = os.path.join(eval_dir, 'bad.txt')
    if not os.path.exists(bad_file):
        print(f'ERROR: {bad_file} が見つかりません', file=sys.stderr)
        sys.exit(1)

    accept = load_accept('evaluate-filter/accept.tsv')
    ignore = load_ignore('evaluate-filter/ignore.txt')

    total_bad = 0
    accepted = 0
    ignored = 0
    real_bad_lines = []

    with open(bad_file) as f:
        for line in f:
            line = line.strip()
            m = re.match(r'\[BAD\]\s+(.+?)\s+=>\s+corpus=(.+?),\s+akaza=(.+)', line)
            if not m:
                continue
            total_bad += 1
            reading = m.group(1)
            akaza = m.group(3)

            if reading in ignore:
                ignored += 1
                continue

            if reading in accept and akaza in accept[reading]:
                accepted += 1
                continue

            real_bad_lines.append(line)

    filtered_bad = len(real_bad_lines)

    print(f'=== Filtered Evaluate Results ===')
    print(f'  Source: {eval_dir}')
    print(f'')
    print(f'  Original BAD:           {total_bad}')
    print(f'  Accepted (style/OK):    {accepted}')
    print(f'  Ignored (ambiguous):    {ignored}')
    print(f'  ─────────────────────')
    print(f'  Real BAD:               {filtered_bad}')
    print(f'  Filtered out:           {accepted + ignored} ({(accepted + ignored) / total_bad * 100:.1f}%)')

    # Save filtered bad
    filtered_bad_file = os.path.join(eval_dir, 'bad-filtered.txt')
    with open(filtered_bad_file, 'w') as f:
        for line in real_bad_lines:
            f.write(line + '\n')
    print(f'')
    print(f'  Filtered BAD saved to: {filtered_bad_file}')


if __name__ == '__main__':
    main()
