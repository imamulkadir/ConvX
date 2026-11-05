from __future__ import annotations

import hashlib
import json
import re
from importlib.resources import files


def registry():
    payload = files("converter.sec_validation").joinpath("efm-v78.2.json").read_bytes()
    return json.loads(payload), hashlib.sha256(payload).hexdigest()


def valid_filename(name, extensions):
    return (
        len(name) <= 32
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) is not None
        and name.lower().endswith(extensions)
    )


def style_problems(value, profile):
    """Conservative literal-value grammar; no claim of exhaustive SEC CSS permissions."""
    if any(c in value for c in "\\{}@!()<>\x00") or "/*" in value or "*/" in value:
        return ["CSS_ACTIVE_OR_COMPLEX"]
    errors = []
    seen = set()
    length = r"-?(?:\d+(?:\.\d+)?|\.\d+)(?:pt|px|em|%)?"
    positive = r"(?:\d+(?:\.\d+)?|\.\d+)(?:pt|px|em|%)?"
    color = r"(?:#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?|black|white|red|blue|green|transparent|inherit)"
    for declaration in value.split(";"):
        if not declaration.strip():
            continue
        if declaration.count(":") != 1:
            errors.append("CSS_SYNTAX")
            continue
        prop, val = (v.strip() for v in declaration.split(":", 1))
        prop = prop.lower()
        if prop in seen:
            errors.append("CSS_DUPLICATE_PROPERTY")
        seen.add(prop)
        if prop not in profile["proposed_style_properties"]:
            errors.append("CSS_PROPERTY_OUTSIDE_PROFILE")
            continue
        grammar = None
        if prop in {"margin", "padding"}:
            grammar = rf"{length if prop == 'margin' else positive}(?:\s+{length if prop == 'margin' else positive}){{0,3}}"
        elif prop in {"margin-left", "vertical-align"}:
            grammar = rf"(?:{length}|baseline|top|bottom|middle|super|sub)"
        elif prop in {"width", "height"}:
            grammar = positive
        elif prop in {"color", "background-color"}:
            grammar = color
        elif prop == "font-family":
            grammar = r"(?:'[A-Za-z][A-Za-z0-9 -]{0,95}'|[A-Za-z][A-Za-z0-9 -]{0,95})"
        elif prop == "font-size":
            grammar = rf"(?:{positive}|inherit)"
        elif prop == "line-height":
            grammar = positive
        elif prop == "display":
            grammar = r"(?:block|inline|inline-block)"
        elif prop == "white-space":
            grammar = r"(?:pre|normal|nowrap)"
        elif prop == "text-decoration":
            grammar = r"(?:none|underline|line-through)"
        elif prop == "page-break-after":
            grammar = r"(?:always|auto)"
        elif prop == "box-sizing":
            grammar = r"(?:border-box|content-box)"
        elif prop == "border-collapse":
            grammar = r"(?:collapse|separate)"
        elif prop == "table-layout":
            grammar = r"(?:fixed|auto)"
        elif prop.startswith("border"):
            grammar = rf"(?:0|{positive}\s+(?:solid|dashed|dotted|double|none)\s+{color})"
        if grammar is None or re.fullmatch(grammar, val) is None:
            errors.append("CSS_VALUE_OUTSIDE_PROFILE")
    return sorted(set(errors))
