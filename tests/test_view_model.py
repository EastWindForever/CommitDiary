import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.diary import DiaryGenerator
from commitdiary.models import GitCommitEntry, GitSnapshot, GitWorkingTreeStatus
from commitdiary.storage import AppSettings
from commitdiary.view_model import CommitDiaryViewModel


class FakeReader:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def read(self, repository_path):
        self.repository_path = repository_path
        return self.snapshot


class FakeHistoryStore:
    def __init__(self):
        self.entries = []

    def append(self, entry):
        self.entries.append(entry)


class FakeSettingsStore:
    def __init__(self):
        self.saved = None

    def save(self, settings):
        self.saved = settings


class CommitDiaryViewModelTests(unittest.TestCase):
    def test_refresh_updates_float_status(self):
        snapshot = _snapshot()
        view_model = CommitDiaryViewModel(
            settings=AppSettings(repository_path=r"D:\Repo"),
            reader=FakeReader(snapshot),
            generator=DiaryGenerator(),
            history_store=FakeHistoryStore(),
            settings_store=FakeSettingsStore(),
        )

        view_model.refresh()

        self.assertEqual("CommitDiary", view_model.repository_name)
        self.assertEqual("main", view_model.branch_name)
        self.assertEqual(1, view_model.today_commit_count)
        self.assertEqual(1, view_model.working_tree_change_count)
        self.assertEqual("feat: add diary generator", view_model.latest_commit_message)

    def test_generate_creates_diary_and_saves_history(self):
        history = FakeHistoryStore()
        view_model = CommitDiaryViewModel(
            settings=AppSettings(repository_path=r"D:\Repo"),
            reader=FakeReader(_snapshot()),
            generator=DiaryGenerator(),
            history_store=history,
            settings_store=FakeSettingsStore(),
        )

        view_model.refresh()
        view_model.generate()

        self.assertIn("今日概览", view_model.diary_markdown)
        self.assertIn("今日完成", view_model.copy_text)
        self.assertEqual(1, len(history.entries))
        self.assertEqual("已生成本地日记", view_model.status_text)
        self.assertTrue(view_model.is_expanded)


def _snapshot():
    return GitSnapshot(
        repository_name="CommitDiary",
        repository_path=r"D:\Repo",
        branch_name="main",
        captured_at=datetime(2026, 6, 27, 19, 0, tzinfo=timezone.utc),
        today_commits=[
            GitCommitEntry(
                hash="abc123",
                message="feat: add diary generator",
                author="Edge",
                committed_at=datetime(2026, 6, 27, 10, 0, tzinfo=timezone.utc),
                changed_files=["src/diary.py"],
            )
        ],
        working_tree=GitWorkingTreeStatus(1, 0, 0, ["src/app.py"]),
    )


if __name__ == "__main__":
    unittest.main()
