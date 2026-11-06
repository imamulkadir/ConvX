"""Versioned product subset: EFM78 5.2.2.5 STYLE plus HTML4 common attributes.

This is a documented interpretation of STYLE, not SEC acceptance or an exhaustive
CSS permission list. The legacy validator retains its unresolved strict behavior.
"""

import hashlib
import json
import re
from html.entities import name2codepoint
from pathlib import Path

from converter.sec_validation.profile import registry, style_problems

PROFILE = "efm78-flow-css2-v1"
STYLE_TAGS = frozenset(
    {"body", "div", "p", "font", "a", "b", "i", "u", "sup", "sub", "table", "tr", "td", "th", "img"}
)
PROPERTIES = frozenset(
    {
        "margin",
        "margin-left",
        "padding",
        "width",
        "height",
        "display",
        "vertical-align",
        "white-space",
        "line-height",
        "font-family",
        "font-size",
        "color",
        "text-decoration",
        "page-break-after",
        "border",
        "border-top",
        "border-bottom",
        "border-left",
        "border-right",
        "background-color",
        "border-collapse",
        "table-layout",
    }
)


def flow_style_allowed(tag):
    return tag in STYLE_TAGS


def flow_profile_digest():
    return hashlib.sha256(
        json.dumps(
            {
                "version": PROFILE,
                "style_tags": sorted(STYLE_TAGS),
                "properties": sorted(PROPERTIES),
                "html4_entities": name2codepoint,
                "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "value_grammar_sha256": hashlib.sha256(
                    Path(__file__).with_name("profile.py").read_bytes()
                ).hexdigest(),
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()


def flow_style_problems(value):
    profile, _ = registry()
    profile["proposed_style_properties"] = sorted(PROPERTIES)
    errors = style_problems(value, profile)
    if re.search(r"(?:^|;)\s*color\s*:\s*transparent\s*(?:;|$)", value, re.I):
        errors.append("CSS_HIDDEN_TEXT")
    return errors
