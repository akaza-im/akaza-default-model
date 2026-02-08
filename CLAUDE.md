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

**重要**: コーパスの単語境界は vibrato (ipadic) のトークナイズ結果に合わせること。ただし読みは vibrato の出力を鵜呑みにせず、文脈に合った正しい読みを書くこと。vibrato は「行って」を「おこなって」、「日本」を「にっぽん」と読むなど、文脈を無視した読みを返すことがある。`scripts/tokenize-line.sh` で単語境界を確認し、読みは自分で正しく付ける。引数でもstdinでも入力可能。

**重要**: bigram モデルは BOS（文頭）・EOS（文末）をトークンとして使用するため、コーパスには原則として完全な文を追加すること。文の断片（例: `ここ/ここ に/に ある/ある`）ではなく、自然な文（例: `ここ/ここ に/に 荷物/にもつ が/が ある/ある`）として登録する。BOS/EOS の bigram が正しく学習されるようにするため。

```bash
# 単一文の確認
./scripts/tokenize-line.sh "買い物に行ってくる"
# => 買い物/かいもの に/に 行って/おこなって くる/くる
# ※ 単語境界(4トークン)は正しいが、読み「おこなって」は誤り
# ※ コーパスでは: 買い物/かいもの に/に 行って/いって くる/くる

# 複数行の確認 (stdin)
echo -e "10時頃に届く\n使用できる" | ./scripts/tokenize-line.sh
# => 10時頃/10じごろ に/に 届く/とどく
# => 使用/しよう できる/できる
```

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

**注意**: anthy コーパスの表記基準に合わせる必要はない。anthy が漢字にしているものを akaza がひらがなで出力する、またはその逆（例: 「ください/下さい」「ない/無い」「もの/物」「こと/事」「いい/良い」等）は表記スタイルの違いであり、誤変換ではない。evaluate の BAD に含まれていてもこれらは改善対象外。

### bigram.model, unigram.model (生成物)

marisa-trie format. Bigram entries: `愛/あい\tは/は => -0.525252`. Scores are `-log10(probability)`.

## Key Tuning Points

- `training-corpus/should.txt` — Add reading→kanji pairs for conversions that the corpus statistics don't cover well (especially colloquial expressions)
- `dict/SKK-JISYO.akaza` — Base system dictionary template. 珍妙な変換（Wikipedia コーパスの偏りで「お題→於大」「これは→之派」のように古典漢字や稀な語が優先される場合）には、正しい複合語エントリを辞書に追加することで対処できる。
- `CORPUS_STATS_VERSION` in Makefile — Version of pre-computed statistics to use

## Release

CalVer (`YYYY.MMDD.PATCH`) format, e.g. `v2026.0201.1`. Pushing a `v*` tag triggers GitHub Actions to build and attach model tarballs to a GitHub Release.

```bash
git tag v2026.0201.1
git push origin v2026.0201.1
```

## CI/CD

GitHub Actions builds the model, evaluates it, and on tagged pushes (`v*`) creates GitHub Releases with the packaged model tarball. The corpus statistics are downloaded from akaza-corpus-stats releases.
