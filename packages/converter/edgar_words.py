"""Verify actual browser-printed words against independent source PDF content."""

from converter.edgar_reflow import source_word_ledger, vertical_plan


def word_geometry(source, printed, layered=False, expected_reflow=None):
    printed_words = printed.get_text("words")
    buckets = {}
    for word in printed_words:
        buckets.setdefault(word[4], []).append(word)
    targets = {}
    if layered:
        planned = vertical_plan(source)["words"]
        if planned != expected_reflow:
            raise ValueError("EDGAR reflow differs from independent source plan")
        targets = {item["index"]: item["target_origin"] for item in planned}
    original = source_word_ledger(source) if layered else source.get_text("words")
    missing, offsets, source_offsets, assembled = 0, [], [], 0
    for ordinal, word in enumerate(original):
        candidates = buckets.get(word[4], [])
        pieces = None
        origin = targets.get(ordinal, word[:2])
        if not candidates and layered:
            for start, first in enumerate(printed_words):
                if (
                    not word[4].startswith(first[4])
                    or abs(first[0] - origin[0]) > 6
                    or abs(first[1] - origin[1]) > 6
                ):
                    continue
                parts, text = [], ""
                for part in printed_words[start : start + 12]:
                    if part not in buckets.get(part[4], []) or (
                        parts and (abs(part[1] - first[1]) > 1.5 or part[0] - parts[-1][2] > 2)
                    ):
                        break
                    parts.append(part)
                    text += part[4]
                    if not word[4].startswith(text):
                        break
                    if text == word[4]:
                        pieces = parts
                        candidates = [
                            (
                                min(p[0] for p in parts),
                                min(p[1] for p in parts),
                                max(p[2] for p in parts),
                                max(p[3] for p in parts),
                                text,
                            )
                        ]
                        break
                if pieces:
                    assembled += 1
                    break
        if not candidates:
            missing += 1
            continue
        nearest = min(candidates, key=lambda c: abs(c[0] - origin[0]) + abs(c[1] - origin[1]))
        offsets.append(max(abs(nearest[0] - origin[0]), abs(nearest[1] - origin[1])))
        source_offsets.append(max(abs(nearest[0] - word[0]), abs(nearest[1] - word[1])))
        if pieces:
            for part in pieces:
                buckets[part[4]].remove(part)
        else:
            candidates.remove(nearest)
    return {
        "missing_words": missing,
        "max_origin_error_pt": max(offsets, default=0),
        "matched_words": len(offsets),
        **(
            {
                "reflowed_words": len(targets),
                "max_source_origin_error_pt": max(source_offsets, default=0),
                "reassembled_words": assembled,
            }
            if layered
            else {}
        ),
    }
