import pytest
from converter.edgar_symbols import canonical_symbol
from converter.sec_validation.flow_profile import flow_style_problems
from converter.sec_validation.layer_profile import layer_style_problems


@pytest.mark.parametrize(
    "font,source,expected",
    [
        ("SymbolMT", "\uf0b7", "\u2022"),
        ("ABCDEF+Symbol", "\uf02a", "\u2217"),
        ("Wingdings-Regular", "\uf0a7", "\u25aa"),
        ("Arial", "\uf0b7", "\uf0b7"),
        ("Symbolish", "\uf02a", "\uf02a"),
        ("Wingdings-Regular", "123.45", "123.45"),
    ],
)
def test_symbol_mapping_requires_verified_font_and_code(font, source, expected):
    assert canonical_symbol(font, source) == expected


@pytest.mark.parametrize(
    "style",
    [
        "overflow:auto",
        "overflow:hidden;overflow:visible",
        "overflow:url(https://example.test)",
        "position:absolute",
        "transform:rotate(90deg)",
        "word-spacing:calc(1pt)",
        "letter-spacing:1e9pt",
    ],
)
def test_layer_policy_rejects_unsupported_active_or_ambiguous_styles(style):
    assert layer_style_problems(style)


def test_rectangular_clipping_profile_is_separate_from_original_flow():
    style = "overflow:hidden;word-spacing:.2pt;letter-spacing:-.01pt"
    assert layer_style_problems(style) == []
    assert flow_style_problems(style)
