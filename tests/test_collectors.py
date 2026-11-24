import unittest
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from smart_daily_system.collectors.feishu import (
    FeishuApiClient,
    FeishuMessageCollector,
    FeishuTaskCollector,
)
from smart_daily_system.collectors.github import GitHubCollector


class FakeTransport:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str | int] | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        self.calls.append(
            {"method": method, "url": url, "headers": headers, "params": params, "body": body}
        )
        return self.responses.pop(0)


class GitHubCollectorTests(unittest.TestCase):
    def test_commit_is_mapped_to_canonical_actor(self) -> None:
        transport = FakeTransport(
            [
                [
                    {
                        "sha": "abc123",
                        "html_url": "https://github.com/example/repo/commit/abc123",
                        "author": {"login": "octocat"},
                        "commit": {
                            "author": {"date": "2026-11-24T01:00:00Z"},
                            "message": "实现采集器\n\n详细说明",
                        },
                    },
                    {
                        "sha": "ignored",
                        "author": {"login": "other"},
                        "commit": {
                            "author": {"date": "2026-11-24T01:00:00Z"},
                            "message": "忽略",
                        },
                    },
                ]
            ]
        )
        collector = GitHubCollector(
            owner="example",
            repository="repo",
            actor_map={"octocat": "alice"},
            transport=transport,
        )

        events = collector.collect(
            actor_ids=("octocat",),
            start_at=datetime(2026, 11, 24, tzinfo=UTC),
            end_at=datetime(2026, 11, 25, tzinfo=UTC),
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].actor, "alice")
        self.assertEqual(events[0].summary, "提交：实现采集器")


class FeishuCollectorTests(unittest.TestCase):
    def test_task_and_message_are_converted(self) -> None:
        transport = FakeTransport(
            [
                {"code": 0, "tenant_access_token": "token", "expire": 7200},
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "guid": "task-1",
                                "summary": "完成任务采集",
                                "completed_at": "2026-11-24T02:00:00Z",
                                "members": [{"open_id": "ou_1"}],
                            }
                        ]
                    },
                },
                {
                    "code": 0,
                    "data": {
                        "items": [
                            {
                                "message_id": "msg-1",
                                "create_time": "1795489200000",
                                "sender": {"id": "ou_2"},
                                "body": {"content": '{"text":"确认接口契约"}'},
                            }
                        ]
                    },
                },
            ]
        )
        client = FeishuApiClient(
            app_id="app",
            app_secret="secret",
            transport=transport,
        )
        start_at = datetime(2026, 11, 24, tzinfo=UTC)
        end_at = datetime(2026, 11, 25, tzinfo=UTC)

        tasks = FeishuTaskCollector(
            client=client,
            actor_map={"ou_1": "alice"},
        ).collect(actor_ids=("ou_1",), start_at=start_at, end_at=end_at)
        messages = FeishuMessageCollector(
            client=client,
            actor_map={"ou_2": "bob"},
            chat_id="chat-1",
        ).collect(actor_ids=("ou_2",), start_at=start_at, end_at=end_at)

        self.assertEqual(tasks[0].actor, "alice")
        self.assertEqual(messages[0].actor, "bob")
        self.assertEqual(messages[0].summary, "沟通：确认接口契约")
        self.assertEqual(transport.calls[1]["headers"]["Authorization"], "Bearer token")


if __name__ == "__main__":
    unittest.main()
