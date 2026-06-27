from __future__ import annotations

from .diary import DiaryGenerator
from .git_reader import GitCliSnapshotReader
from .storage import JsonDiaryHistoryStore, JsonSettingsStore
from .view_model import CommitDiaryViewModel


def build_view_model() -> CommitDiaryViewModel:
    settings_store = JsonSettingsStore.default()
    settings = settings_store.load()
    return CommitDiaryViewModel(
        settings=settings,
        reader=GitCliSnapshotReader(),
        generator=DiaryGenerator(),
        history_store=JsonDiaryHistoryStore.default(),
        settings_store=settings_store,
    )
