#!/usr/bin/env python3
"""分類 TSV の結果を accept.tsv / should.txt / may.txt に適用する。

Usage:
    python3 scripts/apply-classification.py CLASSIFICATION.tsv

分類 TSV のフォーマット:
    reading\tcorpus\takaza\tcategory\tsubcategory\tnotes

カテゴリ別処理:
    style, corpus_wrong → evaluate-filter/accept.tsv に追加
    homophone           → /tmp/homophone-pairs.txt に同音異義語ペア一覧を出力
    colloquial_breakdown, bigram_needed, idiom_unknown → /tmp/should-candidates.txt に候補出力
    number_issue, skip  → スキップ

注意: homophone と should 候補は tokenize-line.sh での検証が必要なため、
      自動追加ではなく候補ファイルを出力する。
"""

import os
import re
import sys


def load_bad_corpus_map():
    """最新の bad.txt から reading→corpus マッピングを作る。"""
    corpus_map = {}
    eval_base = 'tmp/evaluate'
    if not os.path.exists(eval_base):
        return corpus_map
    dirs = sorted(d for d in os.listdir(eval_base)
                  if os.path.isdir(os.path.join(eval_base, d)) and d.startswith('2'))
    for d in reversed(dirs):
        bad_file = os.path.join(eval_base, d, 'bad.txt')
        if os.path.exists(bad_file):
            with open(bad_file) as f:
                for line in f:
                    m = re.match(r'\[BAD\]\s+(.+?)\s+=>\s+corpus=(.+?),\s+akaza=(.+)',
                                 line.strip())
                    if m:
                        corpus_map[m.group(1)] = m.group(2)
            break
    return corpus_map


def main():
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} CLASSIFICATION.tsv', file=sys.stderr)
        sys.exit(1)

    tsv_file = sys.argv[1]
    corpus_map = load_bad_corpus_map()

    # 既存の accept reading を読む
    accept_path = 'evaluate-filter/accept.tsv'
    existing_accept = set()
    if os.path.exists(accept_path):
        with open(accept_path) as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.split('\t')
                if parts:
                    existing_accept.add(parts[0])

    accept_lines = []
    homophone_pairs = []
    should_candidates = []
    skip_count = 0
    number_count = 0

    with open(tsv_file) as f:
        header = f.readline()
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 4:
                continue
            reading, corpus_val, akaza, category = parts[0], parts[1], parts[2], parts[3]
            subcategory = parts[4] if len(parts) > 4 else ''
            notes = parts[5] if len(parts) > 5 else ''

            corpus_expected = corpus_map.get(reading, corpus_val)

            if category in ('style', 'corpus_wrong'):
                if reading not in existing_accept:
                    reason = f'{category}:{subcategory}' if subcategory else category
                    accept_lines.append(f'{reading}\t{akaza}\t{corpus_expected}\t{reason}')

            elif category == 'homophone':
                homophone_pairs.append(f'{subcategory}\t{reading}\t{corpus_expected}\t{akaza}')

            elif category in ('colloquial_breakdown', 'bigram_needed', 'idiom_unknown'):
                should_candidates.append(
                    f'{category}\t{subcategory}\t{reading}\t{corpus_expected}\t{akaza}')

            elif category == 'number_issue':
                number_count += 1
            else:
                skip_count += 1

    # accept.tsv に追記
    if accept_lines:
        with open(accept_path, 'a') as f:
            for line in accept_lines:
                f.write(line + '\n')
        print(f'accept.tsv: +{len(accept_lines)} entries', file=sys.stderr)

    # homophone ペア一覧
    if homophone_pairs:
        outfile = '/tmp/homophone-pairs.txt'
        with open(outfile, 'w') as f:
            for line in homophone_pairs:
                f.write(line + '\n')
        print(f'Homophone pairs: {len(homophone_pairs)} → {outfile}', file=sys.stderr)

    # should 候補一覧
    if should_candidates:
        outfile = '/tmp/should-candidates.txt'
        with open(outfile, 'w') as f:
            for line in should_candidates:
                f.write(line + '\n')
        print(f'Should candidates: {len(should_candidates)} → {outfile}', file=sys.stderr)

    print(f'Skipped: {skip_count}, Number issues: {number_count}', file=sys.stderr)


if __name__ == '__main__':
    main()
