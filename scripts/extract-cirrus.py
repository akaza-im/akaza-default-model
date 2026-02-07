#!/usr/bin/env python3
"""Extract article text from a CirrusSearch NDJSON dump (.json.gz).

Reads a gzip-compressed CirrusSearch content dump via streaming
(no intermediate decompressed file on disk) and writes output in
the same ``<doc>`` format that wikiextractor produces, so the rest
of the Akaza pipeline (``akaza-data tokenize --reader=jawiki``) can
consume it without changes.

Usage:
    python3 scripts/extract-cirrus.py INPUT.json.gz OUTPUT_DIR

Output directory structure mirrors wikiextractor:
    OUTPUT_DIR/AA/wiki_00
    OUTPUT_DIR/AA/wiki_01
    ...
    OUTPUT_DIR/AB/wiki_00
    ...
"""

import gzip
import json
import os
import sys

# Maximum number of articles per output file
ARTICLES_PER_FILE = 1000

# Subdirectory names: AA, AB, AC, ..., ZZ (676 dirs, more than enough)
def _subdir_names():
    for a in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for b in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            yield a + b


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} INPUT.json.gz OUTPUT_DIR", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]

    subdir_iter = _subdir_names()
    current_subdir = next(subdir_iter)
    file_index = 0
    article_count = 0
    out_file = None

    def open_next_file():
        nonlocal current_subdir, file_index, article_count, out_file
        if out_file is not None:
            out_file.close()
        if article_count > 0 and article_count % ARTICLES_PER_FILE == 0:
            file_index += 1
            if file_index >= 100:
                file_index = 0
                current_subdir = next(subdir_iter)
        dir_path = os.path.join(output_dir, current_subdir)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, f"wiki_{file_index:02d}")
        out_file = open(file_path, "a", encoding="utf-8")
        return out_file

    out_file = open_next_file()
    articles_in_current_file = 0
    total_articles = 0

    with gzip.open(input_path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue

            # CirrusSearch NDJSON alternates between index lines and
            # content lines.  Index lines have an "index" key; content
            # lines have the actual article data.
            if "index" in doc:
                continue

            # Only namespace 0 (main articles)
            namespace = doc.get("namespace", -1)
            if namespace != 0:
                continue

            title = doc.get("title", "")
            page_id = doc.get("page_id", "")
            text = doc.get("text", "")

            if not text:
                continue

            # Build the URL the same way wikiextractor does
            url = f"https://ja.wikipedia.org/wiki/{title}"

            out_file.write(f'<doc id="{page_id}" url="{url}" title="{title}">\n')
            out_file.write(text)
            if not text.endswith("\n"):
                out_file.write("\n")
            out_file.write("</doc>\n")

            articles_in_current_file += 1
            total_articles += 1

            if articles_in_current_file >= ARTICLES_PER_FILE:
                article_count = total_articles
                out_file = open_next_file()
                articles_in_current_file = 0

    if out_file is not None:
        out_file.close()

    print(f"Extracted {total_articles} articles to {output_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
