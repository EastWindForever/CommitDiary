from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .ai import AiDiaryRequest, OpenAiCompatibleDiaryEnhancer
from .diary import DiaryGenerator
from .git_reader import GitCliSnapshotReader
from .models import GitSnapshot
from .storage import AppSettings, DiaryHistoryEntry, JsonDiaryHistoryStore, JsonSettingsStore


class SnapshotReader(Protocol):
    def read(self, repository_path: str) -> GitSnapshot:
        ...


class CommitDiaryViewModel:
    def __init__(
        self,
        settings: AppSettings,
        reader: SnapshotReader | None = None,
        generator: DiaryGenerator | None = None,
        history_store: JsonDiaryHistoryStore | None = None,
        settings_store: JsonSettingsStore | None = None,
    ):
        self.settings = settings
        self._reader = reader or GitCliSnapshotReader()
        self._generator = generator or DiaryGenerator()
        self._history_store = history_store or JsonDiaryHistoryStore.default()
        self._settings_store = settings_store or JsonSettingsStore.default()
        self._snapshot: GitSnapshot | None = None
        self.repository_name = "CommitDiary"
        self.branch_name = "-"
        self.today_commit_count = 0
        self.working_tree_change_count = 0
        self.latest_commit_message = "请选择 Git 仓库"
        self.status_text = "待选择仓库"
        self.diary_markdown = ""
        self.copy_text = ""
        self.is_expanded = False

    def refresh(self, repository_path: str | None = None) -> None:
        path = repository_path or self.settings.repository_path
        if not path:
            self.status_text = "请选择 Git 仓库"
            return
        try:
            snapshot = self._reader.read(path)
        except Exception as exc:
            self.status_text = f"扫描失败：{exc}"
            return
        self._snapshot = snapshot
        self.settings = replace(self.settings, repository_path=snapshot.repository_path)
        self.repository_name = snapshot.repository_name
        self.branch_name = snapshot.branch_name
        self.today_commit_count = len(snapshot.today_commits)
        self.working_tree_change_count = snapshot.working_tree.total_changes
        self.latest_commit_message = (
            snapshot.today_commits[0].message if snapshot.today_commits else "今日暂无提交"
        )
        self.status_text = "状态已刷新"
        self._settings_store.save(self.settings)

    def generate(self) -> None:
        if self._snapshot is None:
            self.refresh()
        if self._snapshot is None:
            self.status_text = "请先选择有效仓库"
            return
        draft = self._generator.generate(self._snapshot)
        markdown = draft.markdown
        copy_text = draft.copy_text
        if self.settings.ai_enabled and self.settings.ai_api_key:
            try:
                enhancer = OpenAiCompatibleDiaryEnhancer(
                    self.settings.ai_base_url,
                    self.settings.ai_api_key,
                    self.settings.ai_model,
                )
                result = enhancer.enhance(AiDiaryRequest(self._snapshot, draft.markdown))
                markdown = result.markdown
                copy_text = result.copy_text
                self.status_text = "已生成 AI 增强日记"
            except Exception as exc:
                self.status_text = f"AI 增强失败，已保留本地日记：{exc}"
        else:
            self.status_text = "已生成本地日记"
        self.diary_markdown = markdown
        self.copy_text = copy_text
        self._history_store.append(
            DiaryHistoryEntry(
                repository_name=self._snapshot.repository_name,
                branch_name=self._snapshot.branch_name,
                markdown=markdown,
                copy_text=copy_text,
            )
        )
        self.is_expanded = True

    def update_window_position(self, x: int, y: int, width: int, height: int) -> None:
        self.settings = replace(
            self.settings,
            window_x=x,
            window_y=y,
            window_width=width,
            window_height=height,
        )
        self._settings_store.save(self.settings)

    def update_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self._settings_store.save(self.settings)

    def toggle_expanded(self) -> None:
        self.is_expanded = not self.is_expanded

    def set_expanded(self, value: bool) -> None:
        self.is_expanded = value
