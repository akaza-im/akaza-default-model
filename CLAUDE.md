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

## Model Format

Models use marisa-trie format. Bigram entries look like:
```
愛/あい\tは/は => -0.525252
```
Scores are `-log10(probability)` of n-grams.

## Corpus Files (corpus/)

Three tiers of expected conversion quality, used to correct model bias from Wikipedia/Aozora Bunko:

- **must.txt** — Must convert correctly (10,000 training epochs). Shipping quality gate.
- **should.txt** — Should convert correctly (100 epochs). Send PRs here for new conversions.
- **may.txt** — Nice to have (10 epochs).

Words in corpus files are automatically registered in the system dictionary. The delta parameter (2000) controls corpus influence strength.

## Key Tuning Points

- `mecab-user-dict.csv` — Add terms when Vibrato tokenization fails on known words
- `corpus/should.txt` — Add reading→kanji pairs for conversions Wikipedia/Aozora Bunko don't cover well (especially colloquial expressions)
- `dict/SKK-JISYO.akaza` — Base system dictionary template
- Makefile thresholds: vocab threshold=16, bigram threshold=3

## CI/CD

GitHub Actions builds two model variants (`default` and `kana-preferred`) in a matrix. Tagged pushes (`v*`) create GitHub Releases with packaged model tarballs. The Wikipedia dump is cached between builds to avoid re-downloading.
