"""Separate local EFM78/HTML4 CSS2 clipping profile; legacy/flow-v1 unchanged."""

import hashlib
import re
from pathlib import Path

from converter.sec_validation.flow_profile import flow_profile_digest, flow_style_problems

PROFILE = "efm78-layered-css2-v1"
VERIFIED_REFERENCES = {0x25AA, 0x25CF}


def layer_profile_digest():
    return hashlib.sha256(
        (
            flow_profile_digest()
            + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            + hashlib.sha256(Path(__file__).parents[1].joinpath("edgar_symbols.py").read_bytes()).hexdigest()
        ).encode()
    ).hexdigest()


def layer_style_problems(value):
    retained, seen, errors = [], set(), []
    for item in value.split(";"):
        name = item.split(":", 1)[0].strip().lower()
        if name == "margin" and re.fullmatch(r"margin\s*:\s*0 auto", item.strip()):
            if name in seen:
                errors.append("CSS_DUPLICATE_PROPERTY")
            seen.add(name)
            # Substitute equivalent safe numeric syntax for inherited checking.
            retained.append("margin:0")
            continue
        if name not in {"overflow", "word-spacing", "letter-spacing"}:
            retained.append(item)
            continue
        if name in seen:
            errors.append("CSS_DUPLICATE_PROPERTY")
        seen.add(name)
        grammar = (
            r"overflow\s*:\s*(?:hidden|visible)"
            if name == "overflow"
            else rf"{name}\s*:\s*-?(?:\d+(?:\.\d+)?|\.\d+)(?:pt|px)"
        )
        if not re.fullmatch(grammar, item.strip()):
            errors.append("CSS_VALUE_OUTSIDE_PROFILE")
    return sorted(set(errors + flow_style_problems(";".join(retained))))
