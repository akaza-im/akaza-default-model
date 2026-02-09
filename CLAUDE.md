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

## Evaluate フィルタリング

`evaluate-filter/` に評価結果のフィルタリング定義がある:

- **`accept.tsv`** — `入力読み\t許容するakaza出力\tcorpus期待値\t理由` 形式。スタイル差（ない/無い、もの/物、きれい/綺麗、ダメ/だめ、および/及び 等）や corpus 側の品質問題を記録。corpus期待値列があることで、accept 判断の妥当性を単体で検証可能。
- **`ignore.txt`** — 評価から除外する入力。wordplay（庭には二羽鶏）や意味不明なエントリ。
- **`scripts/filter-evaluate.py`** — bad.txt をフィルタして Real BAD を算出。

accept.tsv に入れてよいもの:
- 漢字↔ひらがな のスタイル差（綺麗/きれい、沢山/たくさん、出来る/できる 等）
- カタカナ↔ひらがな のスタイル差（ダメ/だめ、アホ/あほ 等）
- corpus 側が怪しいケース（再製紙→再生紙 等）
- 短すぎて文脈なしでは判定不能なもの

accept.tsv に入れてはいけないもの:
- Wikipedia 由来の珍語が勝っているケース（艦級、五山 等）→ 修正すべき本当のバグ
- 明らかに日本語として不自然な出力
- **補助動詞のひらがな→漢字変換**: 「書いてはみた」→「書いては見た」は誤り。「みる」は補助動詞なのでひらがなが正しく、「見た」（視覚の意味）にするのは間違い。同様に「やってみる→やって見る」「食べてみた→食べて見た」なども accept に入れてはいけない
- **送り仮名の省略が不自然なケース**: 「集まり」→「集り」は微妙。一般的に違和感がある送り仮名省略は accept に入れない

## BAD エントリの分類方法

`make evaluate` で出力される bad.txt の各エントリは、以下のカテゴリに分類して対処する。

### 1. 表記揺れ（→ accept.tsv）

anthy コーパスと akaza の出力が異なるが、どちらも日本語として正しいケース。修正不要。

- 漢字↔ひらがな: 無い/ない、物/もの、事/こと、良い/いい、出来る/できる、綺麗/きれい、沢山/たくさん
- カタカナ↔ひらがな: ダメ/だめ、アホ/あほ、ゴミ/ごみ、ネコミミ/猫耳
- 送り仮名の差: 引越し/引っ越し、気付/気づ
- 漢字の選択差: 割と/わりと、癖/くせ、奴/やつ、訳/わけ
- 活用表記差: 寝る/ねる、付ける/つける

### 2. 口語分節崩壊（→ should.txt）

口語表現が正しくトークナイズされず、別の漢字列に化けるケース。should.txt で正しい分節を学習させる。

- そういや → 相違や（「そういや」が「相違/や」に分節）
- 使いものにならん → 使い物に並んで諸（「ならんでしょ」が「並んで/諸」に分節）
- 〜たん → 〜単（「減ってたん」が「減って単」に分節）
- しとく → し特化（「心配しとく」が「し/特化」に分節）

### 3. bigram 不足（→ should.txt）

個々の単語は正しく変換できるが、隣接する単語ペアの共起スコアが足りないケース。

- 再コンパイル → 際コンパイル（再/際 の unigram 差）
- ニューヨークダウ → ニューヨークだう（ダウ の bigram 不足）
- 党籍剥奪 → 透析剥奪（党籍/透析 の unigram 差）
- 私用パソコン → 仕様パソコン（私用/仕様 の unigram 差）

### 4. Wikipedia 偏り（→ should.txt）

Wikipedia に頻出する専門用語が日常語のスコアを上回るケース。should.txt で日常語側の bigram を強化する。

- 誤算 → 五山（京都五山で五山のスコアが高い）
- 広告 → 公国（〇〇公国で公国のスコアが高い）
- 変換 → 返還（香港返還等で返還のスコアが高い）

### 5. 熟語不足（→ should.txt or dict/SKK-JISYO.akaza）

辞書やコーパスにない熟語・慣用句。should.txt でエントリ追加、または辞書に複合語として登録。

- 天高く馬肥ゆる → 馬湖ゆる
- 好きな方 → 好き中谷（「なかた」が人名「中谷」に）

### 6. wordplay・意味不明（→ ignore.txt）

文脈なしでは正解が判定できない言葉遊びや、入力自体が意味不明なエントリ。

- 庭には二羽鶏がいた（にわにはにわにわとりがいた）
- 歌がうまいことを疑うまい（うたがうまいことをうたがうまい）
- エンコは速くなりません（スラング、意味不明）

### 7. corpus 側の問題（→ accept.tsv with corpus_wrong）

anthy コーパス自体が間違っている、または古い情報のケース。

- 再製紙 → 再生紙（corpus が「再製紙」だが正しくは「再生紙」）

### 分類の判断基準

1. まず**表記揺れかどうか**を確認。どちらも日本語として自然なら accept.tsv
2. 表記揺れでなければ、**口語崩壊か bigram 不足か**を見る。分節が壊れていれば口語崩壊、分節は正しいが漢字が違えば bigram 不足
3. Wikipedia にしか出ない珍しい語が勝っていれば **Wikipedia 偏り**
4. 辞書にない熟語・慣用句なら**熟語不足**
5. 文自体が評価に適さなければ **ignore.txt**

## コーパス育成の方針

### should.txt に追加すべきパターン
- **一方向の同音異義語**: 書いに行く は非文なので「買いに行く」は安全に追加可能
- **Wikipedia 偏りの矯正**: 五山→誤算、返還→変換 など日常語が Wikipedia 用語に負けるケース
- **分節崩壊の修正**: 口語表現の正しい分節（〜だりして、〜んだろう 等）
- **珍妙変換**: 一般表現が古典漢字や外国人名に化けるケース

### may.txt に追加すべきパターン
- **双方向同音異義語**: 各/書く/核、着る/切る 等（should.txt では退行する）
- **不要カタカナ変換防止**: ジゴロ(時頃)、ドーセ(どうせ)、ッポイ(っぽい) 等

### may.txt 追加時の危険パターン（退行を起こしやすい）
- **助詞と同じ読みを持つ漢字**: 煮/に、荷/に、似/に、値/ね など。助詞「に」が「煮」に変換される大量退行を引き起こす。複合語として辞書に登録する方が安全（例: `しぶかわに /渋皮煮/`）
- **高頻度基本語と同じ読み**: 気/木（き）、見/診（み）、聞/聴（きく）など。片方のスコアを上げると数十件単位の退行が発生する
- **退行チェック**: may.txt 追加後は必ず evaluate を実行し、`煮` `診` `木` など高頻度語の退行が出ていないか確認すること

### corpus-stats の特性（注意点）
- Wikipedia ベースなので日常会話語が弱く、歴史用語・学術用語が過剰に強い
- 外国人名（ミレル、アルカナ等）が高スコアになり、一般的な日本語を侵食する
- 数字+助数詞（NUMBER）は汎化されない: 「2週間」の学習が「1週間」に効かない

## チューニング知見

### 双方向同音異義語の罠

`各/書く/核`、`濃い/恋/鯉/故意`、`着る/切る` のように、同じ読みで3つ以上の漢字がある語は should.txt での調整が極めて困難。一方を強化すると他方が退行する。このような多方向同音異義語は should.txt ではなく、以下の手段で対処する:
- **辞書エントリ (SKK-JISYO.akaza)**: 複合語として登録（例: `かくしせつ /核施設/各施設/`）
- **bigram backoff** や言語モデルの改善（akaza 本体側）

### 退行チェックの必須化

エントリ追加後は必ず evaluate を実行し、前回の BAD リストと diff を取ること。BAD 数が同じでも中身が入れ替わっている可能性がある。特に同音異義語パターンでは、片方を修正すると逆方向の退行が発生しやすい。

**重要**: evaluate の出力は今後並列化により順序が保証されなくなるため、diff を取る際は必ず sort してから比較すること:
```bash
diff <(grep '^\[BAD\]' old/bad.txt | sort) <(grep '^\[BAD\]' new/bad.txt | sort)
```

### 珍妙パターン（Wikipedia コーパスの偏り）

Wikipedia 由来の統計では、歴史上の人物名（勝頼、蒲生等）や古典漢字（憑坐、於大、之派等）が高スコアになることがある。これらは:
- 正しい複合語を辞書に登録する
- コーパスで正しいパターンの bigram を強化する

### 効果的なパターン

以下のパターンは退行を起こしにくく効果が高い:
- **分節崩壊の修正**: 口語表現（〜らん、〜っていう、〜んだろう等）の正しい分節
- **一方向の同音異義語**: 年→都市、鬱→映 など、逆方向の誤変換が少ないもの
- **珍妙変換の修正**: 一般的な表現が古典漢字に変換されるケース

## Release

CalVer (`YYYY.MMDD.PATCH`) format, e.g. `v2026.0201.1`. Pushing a `v*` tag triggers GitHub Actions to build and attach model tarballs to a GitHub Release.

```bash
git tag v2026.0201.1
git push origin v2026.0201.1
```

## CI/CD

GitHub Actions builds the model, evaluates it, and on tagged pushes (`v*`) creates GitHub Releases with the packaged model tarball. The corpus statistics are downloaded from akaza-corpus-stats releases.
