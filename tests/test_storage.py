import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.storage import AppSettings, DiaryHistoryEntry, JsonDiaryHistoryStore, JsonSettingsStore


class StorageTests(unittest.TestCase):
    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonSettingsStore(Path(temp_dir) / "settings.json")
            settings = AppSettings(
                repository_path=r"D:\Code\work\CommitDiary",
                window_x=120,
                window_y=80,
                ai_enabled=True,
                ai_base_url="https://example.test/v1",
                ai_model="gpt-test",
            )

            store.save(settings)
            loaded = store.load()

            self.assertEqual(settings, loaded)

    def test_missing_settings_returns_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = JsonSettingsStore(Path(temp_dir) / "missing.json").load()

            self.assertEqual("", settings.repository_path)
            self.assertFalse(settings.ai_enabled)

    def test_history_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonDiaryHistoryStore(Path(temp_dir) / "history.json")
            entry = DiaryHistoryEntry(
                repository_name="CommitDiary",
                branch_name="main",
                markdown="# 今日概览",
                copy_text="今日完成核心逻辑。",
            )

            store.append(entry)
            loaded = store.load_all()

            self.assertEqual([entry], loaded)


if __name__ == "__main__":
    unittest.main()
