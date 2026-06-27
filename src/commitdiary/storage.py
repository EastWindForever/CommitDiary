from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    repository_path: str = ""
    window_x: int = 100
    window_y: int = 100
    window_width: int = 340
    window_height: int = 260
    ai_enabled: bool = False
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4.1-mini"
    ai_api_key: str = ""


@dataclass(frozen=True)
class DiaryHistoryEntry:
    repository_name: str
    branch_name: str
    markdown: str
    copy_text: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class JsonSettingsStore:
    def __init__(self, path: Path):
        self._path = path

    @classmethod
    def default(cls) -> "JsonSettingsStore":
        return cls(default_data_dir() / "settings.json")

    def load(self) -> AppSettings:
        if not self._path.exists():
            return AppSettings()
        data = json.loads(self._path.read_text(encoding="utf-8"))
        allowed = {field.name for field in AppSettings.__dataclass_fields__.values()}
        clean = {key: value for key, value in data.items() if key in allowed}
        return AppSettings(**clean)

    def save(self, settings: AppSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")


class JsonDiaryHistoryStore:
    def __init__(self, path: Path):
        self._path = path

    @classmethod
    def default(cls) -> "JsonDiaryHistoryStore":
        return cls(default_data_dir() / "history.json")

    def load_all(self) -> list[DiaryHistoryEntry]:
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return [DiaryHistoryEntry(**item) for item in data]

    def append(self, entry: DiaryHistoryEntry) -> None:
        entries = self.load_all()
        entries.append(entry)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(item) for item in entries[-100:]]
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def default_data_dir() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data) / "CommitDiary"
    return Path.home() / ".commitdiary"
