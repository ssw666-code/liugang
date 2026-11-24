from __future__ import annotations

import json
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from smart_daily_system.collectors.base import CollectedEvent
from smart_daily_system.errors import CollectorError
from smart_daily_system.http import JsonTransport


class FeishuApiClient:
    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        transport: JsonTransport,
        base_url: str = "https://open.feishu.cn",
    ) -> None:
        self.app_id = app_id
        self._app_secret = app_secret
        self.transport = transport
        self.base_url = base_url.rstrip("/")
        self._token = ""
        self._token_expires_at = 0.0

    def _tenant_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token
        try:
            payload = self.transport.request_json(
                "POST",
                f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal",
                body={"app_id": self.app_id, "app_secret": self._app_secret},
            )
        except Exception as error:
            raise CollectorError(
                "feishu",
                "FEISHU_AUTH",
                f"Feishu authentication failed: {type(error).__name__}",
            ) from error
        self._ensure_success(payload, "FEISHU_AUTH")
        token = payload.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            raise CollectorError("feishu", "FEISHU_AUTH", "Feishu token missing from response")
        expire = payload.get("expire", 7200)
        expires_in = int(expire) if isinstance(expire, (int, str)) else 7200
        self._token = token
        self._token_expires_at = time.monotonic() + max(expires_in - 60, 60)
        return token

    def search_tasks(self) -> list[dict[str, Any]]:
        payload = self._authorized_request(
            "POST",
            "/open-apis/task/v2/tasks/search",
            body={"page_size": 100},
        )
        return self._items(payload)

    def list_messages(
        self, chat_id: str, start_at: datetime, end_at: datetime
    ) -> list[dict[str, Any]]:
        payload = self._authorized_request(
            "GET",
            "/open-apis/im/v1/messages",
            params={
                "container_id_type": "chat",
                "container_id": chat_id,
                "start_time": str(int(start_at.timestamp())),
                "end_time": str(int(end_at.timestamp())),
                "sort_type": "ByCreateTimeAsc",
                "page_size": 50,
            },
        )
        return self._items(payload)

    def _authorized_request(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, Any] | None = None,
        params: Mapping[str, str | int] | None = None,
    ) -> dict[str, Any]:
        try:
            payload = self.transport.request_json(
                method,
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self._tenant_token()}"},
                params=params,
                body=body,
            )
        except CollectorError:
            raise
        except Exception as error:
            raise CollectorError(
                "feishu",
                "FEISHU_API",
                f"Feishu API request failed: {type(error).__name__}",
            ) from error
        self._ensure_success(payload, "FEISHU_API")
        if not isinstance(payload, dict):
            raise CollectorError("feishu", "FEISHU_RESPONSE", "Feishu response must be an object")
        return payload

    @staticmethod
    def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data")
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]

    @staticmethod
    def _ensure_success(payload: Any, error_code: str) -> None:
        if not isinstance(payload, dict):
            raise CollectorError("feishu", error_code, "Feishu response must be an object")
        code = payload.get("code", 0)
        if code not in (0, "0", None):
            message = payload.get("msg", "unknown API error")
            raise CollectorError("feishu", error_code, f"Feishu API error {code}: {message}")


class FeishuTaskCollector:
    source = "feishu_task"

    def __init__(self, *, client: FeishuApiClient, actor_map: Mapping[str, str]) -> None:
        self.client = client
        self.actor_map = dict(actor_map)

    def collect(
        self,
        *,
        actor_ids: tuple[str, ...],
        start_at: datetime,
        end_at: datetime,
    ) -> list[CollectedEvent]:
        requested = set(actor_ids) if actor_ids else set(self.actor_map)
        events: dict[str, CollectedEvent] = {}
        for item in self.client.search_tasks():
            for external_id in self._task_actors(item):
                if requested and external_id not in requested:
                    continue
                occurred_at = _first_datetime(item, "completed_at", "updated_at", "created_at")
                if occurred_at is None or not (start_at <= occurred_at < end_at):
                    continue
                summary = str(item.get("summary", "")).strip()
                task_id = str(item.get("guid") or item.get("task_id") or "").strip()
                if not summary or not task_id:
                    continue
                event = CollectedEvent(
                    source=self.source,
                    actor=self.actor_map.get(external_id, external_id),
                    occurred_at=occurred_at,
                    summary=f"任务：{summary}",
                    external_id=f"feishu_task:{task_id}",
                    url=str(item.get("url")) if item.get("url") else None,
                )
                events[event.external_id] = event
                break
        return sorted(events.values(), key=lambda event: event.occurred_at)

    @staticmethod
    def _task_actors(item: Mapping[str, Any]) -> tuple[str, ...]:
        found: set[str] = set()
        members = item.get("members")
        if isinstance(members, list):
            for member in members:
                if isinstance(member, dict):
                    for key in ("open_id", "id", "user_id", "member_id"):
                        value = member.get(key)
                        if isinstance(value, str) and value:
                            found.add(value)
        for key in ("owner_id", "creator_id"):
            value = item.get(key)
            if isinstance(value, str) and value:
                found.add(value)
        return tuple(sorted(found))


class FeishuMessageCollector:
    source = "feishu_message"

    def __init__(
        self,
        *,
        client: FeishuApiClient,
        actor_map: Mapping[str, str],
        chat_id: str,
    ) -> None:
        self.client = client
        self.actor_map = dict(actor_map)
        self.chat_id = chat_id

    def collect(
        self,
        *,
        actor_ids: tuple[str, ...],
        start_at: datetime,
        end_at: datetime,
    ) -> list[CollectedEvent]:
        requested = set(actor_ids) if actor_ids else set(self.actor_map)
        if not self.chat_id:
            return []
        events: dict[str, CollectedEvent] = {}
        for item in self.client.list_messages(self.chat_id, start_at, end_at):
            sender = item.get("sender")
            external_id = sender.get("id") if isinstance(sender, dict) else None
            if not isinstance(external_id, str) or (requested and external_id not in requested):
                continue
            occurred_at = _feishu_datetime(item.get("create_time"))
            if occurred_at is None or not (start_at <= occurred_at < end_at):
                continue
            summary = _message_text(item)
            message_id = str(item.get("message_id", "")).strip()
            if not summary or not message_id:
                continue
            event = CollectedEvent(
                source=self.source,
                actor=self.actor_map.get(external_id, external_id),
                occurred_at=occurred_at,
                summary=f"沟通：{summary}",
                external_id=f"feishu_message:{message_id}",
            )
            events[event.external_id] = event
        return sorted(events.values(), key=lambda event: event.occurred_at)


def _first_datetime(item: Mapping[str, Any], *keys: str) -> datetime | None:
    for key in keys:
        value = _feishu_datetime(item.get(key))
        if value is not None:
            return value
    return None


def _feishu_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        number = int(value)
        if number > 10_000_000_000:
            number //= 1000
        return datetime.fromtimestamp(number, tz=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def _message_text(item: Mapping[str, Any]) -> str:
    body = item.get("body")
    content = body.get("content") if isinstance(body, dict) else None
    if not isinstance(content, str):
        return ""
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError:
        return content.strip().replace("\n", " ")
    if isinstance(decoded, dict):
        text = decoded.get("text")
        if isinstance(text, str):
            return text.strip().replace("\n", " ")
    return ""
