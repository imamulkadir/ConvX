from __future__ import annotations

import time
from collections.abc import Callable

from converter.errors import fail


class ProcessingContext:
    def __init__(
        self,
        timeout_seconds: float = 300,
        cancelled: Callable[[], bool] | None = None,
        progress: Callable[[str], None] | None = None,
    ):
        self.deadline = time.monotonic() + timeout_seconds
        self.cancelled = cancelled or (lambda: False)
        self.progress = progress or (lambda stage: None)
        self._next_probe = 0.0

    def check(self) -> None:
        now = time.monotonic()
        if now >= self._next_probe:
            self._next_probe = now + 0.1
            if self.cancelled():
                raise fail(
                    "PROCESSING_CANCELLED",
                    "processing",
                    "Processing was cancelled or its lease was lost",
                    "Start a new authorized attempt",
                )
        if now >= self.deadline:
            raise fail(
                "PROCESSING_TIMEOUT",
                "processing",
                "Processing deadline exceeded",
                "Review document complexity and configured limits",
            )

    def stage(self, name: str) -> None:
        self.check()
        self.progress(name)
