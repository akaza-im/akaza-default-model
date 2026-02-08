#!/usr/bin/env python3
"""Validate corpus and dict/SKK-JISYO.akaza formats."""

import sys
import re
from pathlib import Path


def validate_corpus(path: Path) -> list[str]:
    """Validate corpus file format.

    Expected: space-separated 漢字/よみ tokens per line.
    Lines starting with ;; are comments.
    """
    errors = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line or line.startswith(";;"):
            continue
        tokens = line.split(" ")
        for token in tokens:
            if "/" not in token:
                errors.append(f"{path}:{lineno}: token missing '/': {token!r}")
            elif token.count("/") != 1:
                errors.append(f"{path}:{lineno}: token has multiple '/': {token!r}")
            else:
                surface, reading = token.split("/")
                if not surface:
                    errors.append(f"{path}:{lineno}: empty surface in token: {token!r}")
                if not reading:
                    errors.append(f"{path}:{lineno}: empty reading in token: {token!r}")
    return errors


def validate_skk_dict(path: Path) -> list[str]:
    """Validate SKK dictionary format.

    Expected: よみ /候補1/候補2/.../
    Lines starting with ;; are comments.
    """
    errors = []
    pattern = re.compile(r"^[^ ]+ /.+/$")
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line or line.startswith(";;"):
            continue
        if not pattern.match(line):
            errors.append(f"{path}:{lineno}: invalid format: {line!r}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    errors: list[str] = []

    for corpus in sorted(root.glob("training-corpus/*.txt")):
        errors.extend(validate_corpus(corpus))

    skk = root / "dict" / "SKK-JISYO.akaza"
    if skk.exists():
        errors.extend(validate_skk_dict(skk))

    for e in errors:
        print(e, file=sys.stderr)

    if errors:
        print(f"\n{len(errors)} error(s) found.", file=sys.stderr)
        return 1

    print("All files valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
