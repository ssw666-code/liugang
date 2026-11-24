from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from smart_daily_system.collectors.base import CollectedEvent
from smart_daily_system.errors import CollectorError
from smart_daily_system.http import JsonTransport


class GitHubCollector:
    source = "github"

    def __init__(
        self,
        *,
        owner: str,
        repository: str,
        actor_map: Mapping[str, str],
        token: str = "",
        transport: JsonTransport,
        base_url: str = "https://api.github.com",
        page_limit: int = 10,
    ) -> None:
        self.owner = owner
        self.repository = repository
        self.actor_map = dict(actor_map)
        self.token = token
        self.transport = transport
        self.base_url = base_url.rstrip("/")
        self.page_limit = page_limit

    def collect(
        self,
        *,
        actor_ids: tuple[str, ...],
        start_at: datetime,
        end_at: datetime,
    ) -> list[CollectedEvent]:
        requested = set(actor_ids) if actor_ids else set(self.actor_map)
        if not requested or not self.owner or not self.repository:
            return []

        headers = {"X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        events: dict[str, CollectedEvent] = {}
        try:
            for page in range(1, self.page_limit + 1):
                payload = self.transport.request_json(
                    "GET",
                    f"{self.base_url}/repos/{self.owner}/{self.repository}/commits",
                    headers=headers,
                    params={
                        "since": self._iso_utc(start_at),
                        "until": self._iso_utc(end_at),
                        "per_page": 100,
                        "page": page,
                    },
                )
                if not isinstance(payload, list):
                    raise CollectorError(
                        self.source,
                        "GITHUB_RESPONSE",
                        "GitHub commits response must be a JSON array",
                    )
                for item in payload:
                    event = self._convert_commit(item, requested, start_at, end_at)
                    if event is not None:
                        events[event.external_id] = event
                if len(payload) < 100:
                    break
        except CollectorError:
            raise
        except Exception as error:
            raise CollectorError(
                self.source,
                "GITHUB_COLLECTION",
                f"GitHub collection failed: {type(error).__name__}",
            ) from error
        return sorted(events.values(), key=lambda event: event.occurred_at)

    def _convert_commit(
        self,
        item: Any,
        requested: set[str],
        start_at: datetime,
        end_at: datetime,
    ) -> CollectedEvent | None:
        if not isinstance(item, dict):
            return None
        author = item.get("author")
        login = author.get("login") if isinstance(author, dict) else None
        if not isinstance(login, str) or login not in requested:
            return None
        commit = item.get("commit")
        commit_author = commit.get("author") if isinstance(commit, dict) else None
        date_value = commit_author.get("date") if isinstance(commit_author, dict) else None
        if not isinstance(date_value, str):
            return None
        occurred_at = datetime.fromisoformat(date_value)
        if not (start_at <= occurred_at < end_at):
            return None
        message = commit.get("message", "") if isinstance(commit, dict) else ""
        summary = str(message).splitlines()[0].strip()
        if not summary:
            return None
        sha = item.get("sha")
        if not isinstance(sha, str) or not sha:
            return None
        return CollectedEvent(
            source=self.source,
            actor=self.actor_map.get(login, login),
            occurred_at=occurred_at,
            summary=f"提交：{summary}",
            external_id=f"github:{sha}",
            url=item.get("html_url") if isinstance(item.get("html_url"), str) else None,
        )

    @staticmethod
    def _iso_utc(value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
