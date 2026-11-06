"""Retired API adapter; admission implementation is now converter-owned."""

from converter.admission import validate_docx as validate
from converter.runtime_config import AdmissionError

from app.core.errors import Problem


def validate_docx(path, settings):
    try:
        validate(path, settings)
    except AdmissionError as exc:
        raise Problem(exc.status, exc.code, exc.message) from exc
