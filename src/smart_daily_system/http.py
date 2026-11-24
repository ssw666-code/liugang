from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from smart_daily_system.errors import HttpError


class JsonTransport(Protocol):
    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str | int] | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        """Return decoded JSON or raise HttpError."""
        ...


class JsonHttpClient:
    """Small synchronous JSON client with bounded retries."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        max_retries: int = 2,
        user_agent: str = "SmartDailySystem/1.0",
        sleep: Any = time.sleep,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.user_agent = user_agent
        self._sleep = sleep

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str | int] | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        request_url = f"{url}?{urlencode(params)}" if params else url
        encoded_body = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
        request_headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
            **dict(headers or {}),
        }
        if encoded_body is not None:
            request_headers["Content-Type"] = "application/json; charset=utf-8"

        last_error: HttpError | None = None
        for attempt in range(self.max_retries + 1):
            request = Request(
                request_url,
                data=encoded_body,
                headers=request_headers,
                method=method.upper(),
            )
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                    return self._decode_json(raw, response.status)
            except HTTPError as error:
                last_error = HttpError(
                    "HTTP_STATUS",
                    f"HTTP {error.code} returned by remote service",
                    status_code=error.code,
                )
                if error.code != 429 and error.code < 500:
                    raise last_error from error
            except (TimeoutError, URLError, OSError) as error:
                last_error = HttpError("HTTP_CONNECTION", "Remote service connection failed")
                if attempt >= self.max_retries:
                    raise last_error from error

            if attempt < self.max_retries:
                self._sleep(0.25 * (2**attempt))

        if last_error is not None:
            raise last_error
        raise HttpError("HTTP_UNKNOWN", "HTTP request failed without a response")

    @staticmethod
    def _decode_json(raw: str, status: int) -> Any:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as error:
            raise HttpError("HTTP_JSON", "Remote service returned invalid JSON", status) from error
        return payload
