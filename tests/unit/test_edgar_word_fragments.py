import pytest
from converter.edgar_words import word_geometry


class Page:
    def __init__(self, words):
        self.words = words

    def get_text(self, kind, **kwargs):
        return {"blocks": []} if kind == "rawdict" else self.words


def test_source_bounded_raised_mark_reassembles_before_a_remote_identical_word():
    source = Page([(40, 87, 70, 103, "Index\u00ae", 0, 0, 0)])
    printed = Page(
        [
            (40, 89.25, 64, 103, "Index", 0, 0, 0),
            (65, 87, 70, 94, "\u00ae", 0, 0, 1),
            (200, 300, 230, 316, "Index\u00ae", 1, 0, 0),
        ]
    )
    result = word_geometry(source, printed, True, [])
    assert result["missing_words"] == 0
    assert result["max_origin_error_pt"] == 0
    assert result["reassembled_words"] == 1


@pytest.mark.parametrize("mark", [None, (65, 60, 70, 67, "\u00ae", 0, 0, 1)])
def test_missing_or_displaced_mark_is_not_waived(mark):
    source = Page([(40, 87, 70, 103, "Index\u00ae", 0, 0, 0)])
    words = [(40, 89.25, 64, 103, "Index", 0, 0, 0)]
    if mark:
        words.append(mark)
    words.append((200, 300, 230, 316, "Index\u00ae", 1, 0, 0))
    result = word_geometry(source, Page(words), True, [])
    assert result["missing_words"] or result["max_origin_error_pt"] > 6
