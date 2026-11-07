"""Verified legacy symbol-font PUA mappings; never a general PUA replacement.

Adobe Symbol encoding: unicode.org/Public/MAPPINGS/VENDORS/ADOBE/symbol.txt
Wingdings 1167: unicode.org/wg2/docs/n4143.pdf page27, BLACK SMALL SQUARE.
"""

import re

import pymupdf


def canonical_symbol(font, text):
    font = re.sub(r"^[A-Z]{6}\+", "", font)
    if re.fullmatch(r"Symbol(?:MT)?(?:-Regular)?", font, re.I):
        return text.translate({0xF0B7: 0x2022, 0xF02A: 0x2217})
    if re.fullmatch(r"Wingdings(?:-Regular)?", font, re.I):
        return text.translate({0xF0A7: 0x25AA})
    return text


def source_words(page):
    """Independent native words, interpreting PUA only with source font evidence."""
    words = page.get_text("words")
    raw = None
    for i, word in enumerate(words):
        if not any(0xE000 <= ord(c) <= 0xF8FF for c in word[4]):
            continue
        if raw is None:
            raw = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
        matches = [
            s
            for b in raw["blocks"]
            if b["type"] == 0 and b["number"] == word[5]
            for n, line in enumerate(b["lines"])
            if n == word[6]
            for s in line["spans"]
            if pymupdf.Rect(s["bbox"]).intersects(pymupdf.Rect(word[:4]))
        ]
        fonts = {s["font"] for s in matches}
        if len(fonts) != 1:
            raise ValueError("Ambiguous legacy symbol font")
        words[i] = (*word[:4], canonical_symbol(next(iter(fonts)), word[4]), *word[5:])
    return words
