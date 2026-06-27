from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .models import GitSnapshot


@dataclass(frozen=True)
class AiDiaryRequest:
    snapshot: GitSnapshot
    draft_markdown: str


@dataclass(frozen=True)
class AiDiaryResult:
    markdown: str
    copy_text: str


class OpenAiCompatibleDiaryEnhancer:
    def __init__(self, base_url: str, api_key: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    def enhance(self, request: AiDiaryRequest) -> AiDiaryResult:
        payload = self.build_payload(request, self._model)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"AI 增强失败：{exc}") from exc
        content = data["choices"][0]["message"]["content"].strip()
        return AiDiaryResult(markdown=content, copy_text=_extract_copy_text(content))

    @staticmethod
    def build_payload(request: AiDiaryRequest, model: str) -> dict:
        snapshot = request.snapshot
        commits = [
            {
                "hash": commit.hash[:7],
                "message": commit.message,
                "author": commit.author,
                "changed_files": commit.changed_files,
            }
            for commit in snapshot.today_commits
        ]
        context = {
            "repository": snapshot.repository_name,
            "branch": snapshot.branch_name,
            "today_commit_count": len(snapshot.today_commits),
            "working_tree_change_count": snapshot.working_tree.total_changes,
            "commits": commits,
            "working_tree_files": snapshot.working_tree.changed_files,
            "draft_markdown": request.draft_markdown,
        }
        return {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是开发日报助手，请基于摘要级 Git 上下文生成中文开发日记。",
                },
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False),
                },
            ],
            "temperature": 0.2,
        }


class DisabledAiDiaryEnhancer:
    def enhance(self, request: AiDiaryRequest) -> AiDiaryResult:
        raise RuntimeError("AI 增强未启用")


def _extract_copy_text(markdown: str) -> str:
    lines = [line.strip("#- ` ") for line in markdown.splitlines() if line.strip()]
    return " ".join(lines[:4]).strip() or markdown.strip()
