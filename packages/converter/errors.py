from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Diagnostic:
    code: str
    stage: str
    description: str
    remediation: str
    file: str | None = None
    element: str | None = None
    page: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class ConversionFailure(Exception):
    def __init__(self, diagnostic: Diagnostic):
        self.diagnostic = diagnostic
        super().__init__(diagnostic.code)


def fail(code: str, stage: str, description: str, remediation: str, **location) -> ConversionFailure:
    return ConversionFailure(Diagnostic(code, stage, description, remediation, **location))
