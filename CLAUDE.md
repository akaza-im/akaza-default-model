# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository generates the default language model and system dictionary for **Akaza**, a Japanese kana-kanji conversion engine (IME). It is a data engineering pipeline, not a traditional software project. The pipeline downloads Japanese text corpora (Wikipedia + Aozora Bunko), tokenizes them, computes n-gram statistics, and produces marisa-trie format models.

## Build Commands

The build requires `akaza-data` (Rust tool from https://github.com/akaza-im/akaza.git), `wikiextractor` (Python), `wget`, `bunzip2`, `unzip`, and system libraries (`libmarisa-dev`, `clang`, `libibus-1.0-dev`).

```bash
# Install akaza-data
cargo install --git https://github.com/akaza-im/akaza.git akaza-data

# Build everything (downloads ~1GB Wikipedia dump on first run)
make

# Build kana-preferred variant
TOKENIZER_OPTS=--kana-preferred make

# Evaluate model against anthy test corpus
make evaluate

# Install to system (default PREFIX=/usr)
make install
```

Git submodules (`skk-dev-dict`, `aozorabunko_text`) must be initialized before building.

## Pipeline Architecture

The Makefile encodes a linear data pipeline:

1. **Download & extract** Japanese Wikipedia dump → `work/jawiki/`
2. **Tokenize** Wikipedia and Aozora Bunko texts using Vibrato (MeCab-compatible) with IPADIC dictionary → `work/jawiki/vibrato-ipadic/`, `work/aozora_bunko/vibrato-ipadic/`
3. **Compute word frequencies** (wfreq) across all tokenized sources + corpus files → `work/vibrato-ipadic.wfreq`
4. **Build vocabulary** with frequency threshold=16 → `work/vibrato-ipadic.vocab`
5. **Generate unigram/bigram word count tries** (bigram threshold=3) → `work/stats-vibrato-*.wordcnt.trie`
6. **Train models** by applying corpus corrections with `learn-corpus` → `data/unigram.model`, `data/bigram.model`
7. **Build system dictionary** from vocab + corpus + UniDic katakana terms, excluding SKK-JISYO.L entries → `data/SKK-JISYO.akaza`
8. **Evaluate** against anthy-corpus test sets (corpus.4.txt is excluded — it contains known error cases)

## Data Formats

### corpus/*.txt (学習コーパス)

`漢字/よみ` のスペース区切り。`;; ` で始まる行はコメント。

```
僕/ぼく の/の 主観/しゅかん では/では そう/そう です/です
```

Three tiers with different training epoch counts:
- **must.txt** — Must convert correctly (10,000 epochs). Shipping quality gate.
- **should.txt** — Should convert correctly (100 epochs). Send PRs here.
- **may.txt** — Nice to have (10 epochs).

Words in corpus files are automatically registered in the system dictionary. Delta parameter (2000) controls corpus influence strength.

### mecab-user-dict.csv

Vibrato (MeCab互換) user dictionary CSV. Add words that Vibrato fails to tokenize.

```
令和,1288,1288,5904,名詞,固有名詞,一般,*,*,*,令和,レイワ,レイワ
```

Fields: `表層形,左文脈ID,右文脈ID,コスト,品詞,品詞細分類1,品詞細分類2,品詞細分類3,活用型,活用形,原形,読み,発音`

### dict/SKK-JISYO.akaza

SKK dictionary format. For vocabulary not in SKK-JISYO.L.

```
きめつのやいば /鬼滅の刃/
かなにゅうりょく /かな入力/仮名入力/
```

Format: `よみ /候補1/候補2/.../`

### anthy-corpus/*.txt (評価用コーパス)

Evaluation data from anthy-unicode. Each line is pipe-delimited reading + expected kanji pair.

```
|さとう|」|です| |佐藤|」|です|
```

First half is readings (hiragana), space separator, second half is expected conversion. corpus.4.txt is excluded from evaluation (contains known error cases).

### bigram.model, unigram.model (生成物)

marisa-trie format. Bigram entries: `愛/あい\tは/は => -0.525252`. Scores are `-log10(probability)`.

## Key Tuning Points

- `mecab-user-dict.csv` — Add terms when Vibrato tokenization fails on known words
- `corpus/should.txt` — Add reading→kanji pairs for conversions Wikipedia/Aozora Bunko don't cover well (especially colloquial expressions)
- `dict/SKK-JISYO.akaza` — Base system dictionary template
- Makefile thresholds: vocab threshold=16, bigram threshold=3

## Release

CalVer (`YYYY.MMDD.PATCH`) format, e.g. `v2026.0201.1`. Pushing a `v*` tag triggers GitHub Actions to build and attach model tarballs to a GitHub Release.

```bash
git tag v2026.0201.1
git push origin v2026.0201.1
```

## Local Build Notes

ローカルにはディスクに余裕があるので、CI のように中間ファイル（jawiki XML 等）を削除する必要はない。`work/` 以下の中間成果物はそのまま残してよい。

wikiextractor は Python 3.11+ で動かないため、mise で Python 3.10 を使う (`.mise.toml` で設定済み)。

## CI/CD

GitHub Actions builds two model variants (`default` and `kana-preferred`) in a matrix. Tagged pushes (`v*`) create GitHub Releases with packaged model tarballs. The Wikipedia dump is cached between builds to avoid re-downloading.
