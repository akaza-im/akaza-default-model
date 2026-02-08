# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository generates the default language model and system dictionary for **Akaza**, a Japanese kana-kanji conversion engine (IME). It downloads pre-computed corpus statistics from [akaza-corpus-stats](https://github.com/akaza-im/akaza-corpus-stats) releases, trains models using corpus corrections, and produces marisa-trie format models.

## Build Commands

The build requires `akaza-data` (Rust tool from https://github.com/akaza-im/akaza.git), `gh` (GitHub CLI), `wget`, `unzip`, and system libraries (`libmarisa-dev`, `clang`, `libibus-1.0-dev`).

```bash
# Install akaza-data
cargo install --git https://github.com/akaza-im/akaza.git akaza-data

# Build everything (downloads corpus-stats tarball on first run)
make

# Evaluate model against anthy test corpus
make evaluate

# Install to system (default PREFIX=/usr)
make install
```

Git submodule (`skk-dev-dict`) must be initialized before building.

## Pipeline Architecture

The Makefile encodes a linear data pipeline:

1. **Download corpus statistics** from akaza-corpus-stats GitHub Release → `work/` (wordcnt tries + vocab)
2. **Train models** by applying corpus corrections with `learn-corpus` → `data/unigram.model`, `data/bigram.model`
3. **Build system dictionary** from vocab + corpus + UniDic katakana terms, excluding SKK-JISYO.L entries → `data/SKK-JISYO.akaza`
4. **Evaluate** against anthy-corpus test sets (corpus.4.txt is excluded — it contains known error cases)

## Data Formats

### training-corpus/*.txt (学習コーパス)

`漢字/よみ` のスペース区切り。`;; ` で始まる行はコメント。

```
僕/ぼく の/の 主観/しゅかん では/では そう/そう です/です
```

Three tiers with different training epoch counts:
- **must.txt** — Must convert correctly (10,000 epochs). Shipping quality gate.
- **should.txt** — Should convert correctly (100 epochs). Send PRs here.
- **may.txt** — Nice to have (10 epochs).

Words in corpus files are automatically registered in the system dictionary. Delta parameter (2000) controls corpus influence strength.

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

- `training-corpus/should.txt` — Add reading→kanji pairs for conversions that the corpus statistics don't cover well (especially colloquial expressions)
- `dict/SKK-JISYO.akaza` — Base system dictionary template
- `CORPUS_STATS_VERSION` in Makefile — Version of pre-computed statistics to use

## Release

CalVer (`YYYY.MMDD.PATCH`) format, e.g. `v2026.0201.1`. Pushing a `v*` tag triggers GitHub Actions to build and attach model tarballs to a GitHub Release.

```bash
git tag v2026.0201.1
git push origin v2026.0201.1
```

## CI/CD

GitHub Actions builds the model, evaluates it, and on tagged pushes (`v*`) creates GitHub Releases with the packaged model tarball. The corpus statistics are downloaded from akaza-corpus-stats releases.
