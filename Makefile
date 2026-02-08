PREFIX ?= /usr
DATADIR ?= $(PREFIX)/share
DESTDIR ?=
MODELDIR ?= $(DESTDIR)$(DATADIR)/akaza/model/default/

CORPUS_STATS_VERSION ?= v2026.0208.0

all: data/bigram.model \
	 data/SKK-JISYO.akaza

# -------------------------------------------------------------------------
# corpus-stats tarball ダウンロード
# -------------------------------------------------------------------------

work/corpus-stats/_SUCCESS:
	mkdir -p work/
	gh release download $(CORPUS_STATS_VERSION) \
		--repo akaza-im/akaza-corpus-stats \
		--pattern 'akaza-corpus-stats.tar.gz' \
		--output work/akaza-corpus-stats.tar.gz
	tar xzf work/akaza-corpus-stats.tar.gz -C work/
	rm work/akaza-corpus-stats.tar.gz
	mkdir -p work/corpus-stats && touch work/corpus-stats/_SUCCESS

# -------------------------------------------------------------------------
#  Unidic の処理
# -------------------------------------------------------------------------

work/unidic/unidic.zip:
	mkdir -p work/unidic/
	wget --no-verbose --no-clobber -O work/unidic/unidic.zip https://clrd.ninjal.ac.jp/unidic_archive/csj/3.1.1/unidic-csj-3.1.1.zip

work/unidic/lex_3_1.csv: work/unidic/unidic.zip
	unzip -D -o -j work/unidic/unidic.zip -d work/unidic/
	touch work/unidic/lex_3_1.csv

# -------------------------------------------------------------------------

# 統計的仮名かな漢字変換のためのモデル作成処理

data/bigram.model: work/corpus-stats/_SUCCESS corpus/must.txt corpus/should.txt corpus/may.txt data/SKK-JISYO.akaza
	akaza-data learn-corpus \
		--delta=2000 \
		--may-epochs=10 \
		--should-epochs=100 \
		--must-epochs=10000 \
		corpus/may.txt \
		corpus/should.txt \
		corpus/must.txt \
		work/stats-vibrato-unigram.wordcnt.trie work/stats-vibrato-bigram.wordcnt.trie \
		data/unigram.model data/bigram.model \
		-v

data/unigram.model: data/bigram.model

# -------------------------------------------------------------------------

# システム辞書の構築。dict/SKK-JISYO.akaza、コーパスに書かれている語彙および work/vibrato-ipadic.vocab にある語彙。
# から、SKK-JISYO.L に含まれる語彙を除いたものが登録されている。

data/SKK-JISYO.akaza: work/corpus-stats/_SUCCESS dict/SKK-JISYO.akaza corpus/must.txt corpus/should.txt corpus/may.txt work/unidic/lex_3_1.csv
	akaza-data make-dict \
		--corpus corpus/must.txt \
		--corpus corpus/should.txt \
		--corpus corpus/may.txt \
		--unidic work/unidic/lex_3_1.csv \
		--vocab work/vibrato-ipadic.vocab \
		data/SKK-JISYO.akaza \
		-vvv

# -------------------------------------------------------------------------

# corpus.4.txt は誤変換をおさめたものなので評価用には使わない
evaluate: data/bigram.model
	akaza-data evaluate \
		 --corpus=anthy-corpus/corpus.0.txt \
		 --corpus=anthy-corpus/corpus.1.txt \
		 --corpus=anthy-corpus/corpus.2.txt \
		 --corpus=anthy-corpus/corpus.3.txt \
		 --corpus=anthy-corpus/corpus.5.txt \
		 --eucjp-dict=skk-dev-dict/SKK-JISYO.L \
		 --utf8-dict=data/SKK-JISYO.akaza \
		 --model-dir=data/ \
		 -vv

# -------------------------------------------------------------------------

install:
	install -m 0755 -d $(MODELDIR)
	install -m 0644 data/*.model $(MODELDIR)
	install -m 0644 data/SKK-JISYO.* $(MODELDIR)

# -------------------------------------------------------------------------

.PHONY: all install evaluate
