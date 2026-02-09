#!/usr/bin/env python3
"""bad-filtered.txt からランダムサンプルを抽出する。

Usage:
    python3 scripts/sample-bad.py [N] [--exclude FILE...]

引数:
    N               サンプル数（デフォルト: 100）
    --exclude FILE  除外する過去のサンプルファイル（複数指定可）

出力:
    /tmp/bad-sample-{N}.txt にサンプルを保存
"""

import argparse
import os
import random
import re
import sys


def main():
    parser = argparse.ArgumentParser(description='bad-filtered.txt からランダムサンプルを抽出')
    parser.add_argument('n', nargs='?', type=int, default=100, help='サンプル数')
    parser.add_argument('--exclude', nargs='*', default=[], help='除外する過去サンプルファイル')
    parser.add_argument('--seed', type=int, default=None, help='乱数シード')
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # 最新の evaluate ディレクトリを探す
    eval_base = 'tmp/evaluate'
    dirs = sorted(d for d in os.listdir(eval_base)
                  if os.path.isdir(os.path.join(eval_base, d)) and d.startswith('2'))
    if not dirs:
        print('ERROR: evaluate ディレクトリが見つかりません', file=sys.stderr)
        sys.exit(1)
    eval_dir = os.path.join(eval_base, dirs[-1])

    # filter-evaluate を実行して最新の bad-filtered.txt を生成
    bad_filtered = os.path.join(eval_dir, 'bad-filtered.txt')
    if not os.path.exists(bad_filtered):
        print(f'filter-evaluate.py を実行中...', file=sys.stderr)
        os.system(f'python3 scripts/filter-evaluate.py {eval_dir}')

    if not os.path.exists(bad_filtered):
        print(f'ERROR: {bad_filtered} が見つかりません', file=sys.stderr)
        sys.exit(1)

    # 除外 reading を収集
    exclude_readings = set()
    for excl_file in args.exclude:
        if not os.path.exists(excl_file):
            continue
        with open(excl_file) as f:
            for line in f:
                m = re.match(r'\[BAD\]\s+(.+?)\s+=>', line.strip())
                if m:
                    exclude_readings.add(m.group(1))

    # accept.tsv の reading も除外（既に処理済み）
    accept_path = 'evaluate-filter/accept.tsv'
    if os.path.exists(accept_path):
        with open(accept_path) as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.split('\t')
                if parts:
                    exclude_readings.add(parts[0])

    # 候補を収集
    candidates = []
    with open(bad_filtered) as f:
        for line in f:
            line = line.strip()
            m = re.match(r'\[BAD\]\s+(.+?)\s+=>', line)
            if m and m.group(1) not in exclude_readings:
                candidates.append(line)

    n = min(args.n, len(candidates))
    sample = random.sample(candidates, n)

    outfile = f'/tmp/bad-sample-{n}.txt'
    with open(outfile, 'w') as f:
        for s in sample:
            f.write(s + '\n')

    print(f'Sampled {n} from {len(candidates)} candidates '
          f'(excluded {len(exclude_readings)} readings)', file=sys.stderr)
    print(f'Saved to: {outfile}', file=sys.stderr)
    print(outfile)


if __name__ == '__main__':
    main()
