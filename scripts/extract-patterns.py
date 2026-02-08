#!/usr/bin/env python3
"""evaluate 出力から誤変換パターンを抽出し、LLM 用プロンプトを生成する。

使い方:
    make evaluate 2>&1 | python3 scripts/extract-patterns.py

evaluate を既に実行済みなら:
    make evaluate 2>&1 > /tmp/eval.txt
    python3 scripts/extract-patterns.py < /tmp/eval.txt
"""

import sys
import re
from collections import Counter, defaultdict


# 表記揺れ (後回し): 漢字の開き閉じ・送り仮名・カタカナひらがな
# これらは anthy-corpus の好みの問題であり、Akaza としてどちらでも許容できる
SKIP_PATTERNS = {
    # 漢字の開き閉じ
    ("無", "な"), ("な", "無"),
    ("事", "こと"), ("こと", "事"),
    ("物", "もの"), ("もの", "物"),
    ("良", "よ"), ("よ", "良"),
    ("付", "つ"), ("つ", "付"),
    ("後", "あと"), ("あと", "後"),
    ("他", "ほか"), ("ほか", "他"),
    ("見", "み"), ("み", "見"),
    ("寝", "ね"), ("ね", "寝"),
    ("来", "き"), ("き", "来"),
    ("くだ", "下"), ("下", "くだ"),
    ("出来", "でき"), ("でき", "出来"),
    ("色々", "いろいろ"), ("いろいろ", "色々"),
    ("おもしろ", "面白"), ("面白", "おもしろ"),
    ("きれい", "綺麗"), ("綺麗", "きれい"),
    ("ほど", "程"), ("程", "ほど"),
    ("位", "ぐらい"), ("ぐらい", "位"),
    ("すべ", "全"), ("全", "すべ"),
    ("何", "なん"), ("なん", "何"),
    ("何", "なに"), ("なに", "何"),
    ("所", "ところ"), ("ところ", "所"),
    ("所", "どころ"), ("どころ", "所"),
    ("間", "あいだ"), ("あいだ", "間"),
    ("確", "たし"), ("たし", "確"),
    ("沢山", "たくさん"), ("たくさん", "沢山"),
    ("方", "ほう"), ("ほう", "方"),
    ("訳", "わけ"), ("わけ", "訳"),
    ("毎", "ごと"), ("ごと", "毎"),
    ("頃", "ころ"), ("ころ", "頃"),
    ("為", "ため"), ("ため", "為"),
    ("通", "とお"), ("とお", "通"),
    ("辺", "あた"), ("あた", "辺"),
    ("様", "よう"), ("よう", "様"),
    ("筈", "はず"), ("はず", "筈"),
    ("迄", "まで"), ("まで", "迄"),
    ("又", "また"), ("また", "又"),
    ("既", "すで"), ("すで", "既"),
    ("殆", "ほとん"), ("ほとん", "殆"),
    ("我", "わ"), ("わ", "我"),
    ("乍ら", "ながら"), ("ながら", "乍ら"),
    ("まった", "全"), ("全", "まった"),  # まったく / 全く
    ("うれ", "嬉"), ("嬉", "うれ"),  # うれしい / 嬉しい
    ("辛", "つら"), ("つら", "辛"),  # 辛い / つらい
    ("一人", "ひとり"), ("ひとり", "一人"),
    ("二人", "ふたり"), ("ふたり", "二人"),
    ("上手", "うま"), ("うま", "上手"),  # 上手く / うまく
    ("不味", "まず"), ("まず", "不味"),
    ("渡", "わた"), ("わた", "渡"),  # 渡って / わたって
    ("開", "ひら"), ("ひら", "開"),  # 開ける / ひらける
    ("しゃべ", "喋"), ("喋", "しゃべ"),
    ("がんば", "頑張"), ("頑張", "がんば"),
    ("つづ", "続"), ("続", "つづ"),
    ("どお", "通"), ("通", "どお"),  # どおり / 通り
    ("もと", "元"), ("元", "もと"),
    ("跡", "あと"), ("あと", "跡"),
    ("わり", "割"), ("割", "わり"),  # わりと / 割と
    ("とき", "時"), ("時", "とき"),
    ("みてくだ", "見て下"), ("見て下", "みてくだ"),  # みてください / 見て下さい
    ("台詞", "セリフ"), ("セリフ", "台詞"),
    ("一発", "イッパツ"), ("イッパツ", "一発"),
    ("マンガ", "漫画"), ("漫画", "マンガ"),
    ("アホ", "あほ"), ("あほ", "アホ"),
    ("ぽい", "ポイ"), ("ポイ", "ぽい"),
    ("なぜ", "何故"), ("何故", "なぜ"),
    ("欲しい物", "ほしいもの"), ("ほしいもの", "欲しい物"),
    # カタカナひらがな
    ("ダメ", "だめ"), ("だめ", "ダメ"),
    ("ゴミ", "ごみ"), ("ごみ", "ゴミ"),
    ("たぶん", "多分"), ("多分", "たぶん"),
    ("キレイ", "きれい"), ("きれい", "キレイ"),
    ("ダメ", "駄目"), ("駄目", "ダメ"),
    # 記号
    ("?", "？"), ("？", "?"),
    ("!", "！"), ("！", "!"),
    ("…", "。。。"), ("。。。", "…"),
}

# 1文字同士の差分 (ノイズが多い)
MIN_DIFF_LEN = 2


def extract_diff(corpus: str, akaza: str) -> tuple[str, str] | None:
    """2つの文字列の前方一致・後方一致を除いた差分を返す。"""
    i = 0
    while i < len(corpus) and i < len(akaza) and corpus[i] == akaza[i]:
        i += 1
    j_c, j_a = len(corpus) - 1, len(akaza) - 1
    while j_c > i and j_a > i and corpus[j_c] == akaza[j_a]:
        j_c -= 1
        j_a -= 1

    c_diff = corpus[i:j_c + 1]
    a_diff = akaza[i:j_a + 1]

    if not c_diff or not a_diff:
        return None
    return c_diff, a_diff


def main() -> None:
    lines = sys.stdin.readlines()
    bad_lines = [l.strip() for l in lines if l.startswith("[BAD]")]

    if not bad_lines:
        print("ERROR: [BAD] 行が見つかりません。make evaluate の出力を stdin に渡してください。",
              file=sys.stderr)
        sys.exit(1)

    confusion: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)

    for line in bad_lines:
        m = re.match(r"\[BAD\] (.+) => corpus=(.+), akaza=(.+)", line)
        if not m:
            continue
        reading = m.group(1)
        corpus_text = m.group(2)
        akaza_text = m.group(3)

        # 数字全角半角の差分のみ → スキップ
        c_norm = re.sub(r"[０-９]", lambda m: chr(ord(m.group()) - 0xFEE0), corpus_text)
        a_norm = re.sub(r"[０-９]", lambda m: chr(ord(m.group()) - 0xFEE0), akaza_text)
        if c_norm == a_norm:
            continue

        diff = extract_diff(corpus_text, akaza_text)
        if diff is None:
            continue
        c_diff, a_diff = diff
        if (c_diff, a_diff) in SKIP_PATTERNS:
            continue
        if len(c_diff) < MIN_DIFF_LEN and len(a_diff) < MIN_DIFF_LEN:
            continue

        confusion[(c_diff, a_diff)] += 1
        if len(examples[(c_diff, a_diff)]) < 3:
            examples[(c_diff, a_diff)].append((reading, corpus_text, akaza_text))

    # --- カテゴリ分類 ---
    # 分節崩壊: 語尾パターンが壊れるもの (must 候補)
    segmentation_failures = {}
    # 同音異義語 (should 候補)
    homophones = {}
    # その他 (may 候補)
    others = {}

    # Wikipedia コーパスの偏り (固有名詞・専門用語) や語尾の誤分節が原因
    # wrong 側にこれらの文字列が含まれていたら分節崩壊として分類
    segmentation_keywords = {
        "消化", "益代", "マスネ", "ナイン", "邦画", "語句", "砂", "鐘", "米", "北",
        "須賀", "ナノカ", "ンデス",  # Wikipedia 固有名詞の影響
        "歌", "荷",  # 語尾の誤分節 (〜ですか→〜です歌, 〜にも→荷も)
    }

    for (correct, wrong), count in confusion.most_common():
        if count < 3:
            break
        if any(kw in wrong for kw in segmentation_keywords):
            segmentation_failures[(correct, wrong)] = count
        else:
            homophones[(correct, wrong)] = count

    # --- 出力 ---
    print("=" * 70)
    print("分節崩壊パターン (must 候補)")
    print("Wikipedia コーパスの偏りや語尾の誤分節が原因")
    print("=" * 70)
    for (correct, wrong), count in sorted(
        segmentation_failures.items(), key=lambda x: -x[1]
    ):
        exs = examples[(correct, wrong)]
        print(f"  {correct} → {wrong}  ({count}回)")
        for _, corpus_text, akaza_text in exs[:1]:
            print(f"    期待: {corpus_text}")
            print(f"    実際: {akaza_text}")

    print()
    print("=" * 70)
    print("同音異義語・その他パターン (should 候補)")
    print("=" * 70)
    for (correct, wrong), count in sorted(
        homophones.items(), key=lambda x: -x[1]
    ):
        exs = examples[(correct, wrong)]
        print(f"  {correct} → {wrong}  ({count}回)")
        for _, corpus_text, akaza_text in exs[:1]:
            print(f"    期待: {corpus_text}")
            print(f"    実際: {akaza_text}")

    # --- LLM プロンプト生成 ---
    print()
    print("=" * 70)
    print("LLM プロンプト (以下をそのまま LLM に渡してください)")
    print("=" * 70)

    all_patterns = []
    for (correct, wrong), count in sorted(
        segmentation_failures.items(), key=lambda x: -x[1]
    ):
        all_patterns.append((correct, wrong, count, "must"))
    for (correct, wrong), count in sorted(
        homophones.items(), key=lambda x: -x[1]
    ):
        all_patterns.append((correct, wrong, count, "should"))

    # バッチに分割 (20パターンずつ)
    batch_size = 20
    for batch_idx in range(0, len(all_patterns), batch_size):
        batch = all_patterns[batch_idx:batch_idx + batch_size]
        print(f"\n--- バッチ {batch_idx // batch_size + 1} ---\n")
        print("以下の同音異義語・誤変換パターンについて、「正しい方」が自然に使われる日本語文を各2つ生成してください。")
        print("出力は `漢字/よみ スペース区切り` のコーパス形式でお願いします。")
        print("1文は10〜30字程度。口語・書き言葉どちらでも可。")
        print("各単語を `表層形/読み` のペアにし、スペースで区切ってください。")
        print()
        print("出力例:")
        print("この/この 機能/きのう を/を 使用/しよう する/する")
        print("性能/せいのう の/の 向上/こうじょう を/を 目指す/めざす")
        print()
        print("パターン一覧:")
        for correct, wrong, count, tier in batch:
            print(f"- 「{correct}」が正しいのに「{wrong}」と誤変換される")
        print()


if __name__ == "__main__":
    main()
