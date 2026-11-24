from __future__ import annotations


class SmartDailyError(RuntimeError):
    """Base class for expected application failures."""


class CollectorError(SmartDailyError):
    """A collector could not complete a source-level operation."""

    def __init__(self, source: str, code: str, message: str) -> None:
        super().__init__(message)
        self.source = source
        self.code = code


class HttpError(SmartDailyError):
    """The HTTP adapter received or produced an invalid response."""

    def __init__(self, code: str, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class DeliveryError(SmartDailyError):
    """A report sender could not deliver the report."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
