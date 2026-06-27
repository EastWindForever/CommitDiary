import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.desktop_app import (
    COMPACT_WINDOW_SIZE,
    MINI_METRIC_LABELS,
    PRIMARY_ACTION_LABELS,
    SETTINGS_FIELD_LABELS,
    VIEW_NAMES,
    CommitDiaryDesktopApp,
)


class DesktopUiTests(unittest.TestCase):
    def test_primary_actions_include_repository_picker(self):
        self.assertIn("选择", PRIMARY_ACTION_LABELS)

    def test_main_window_owns_settings_controls(self):
        self.assertIn("dashboard", VIEW_NAMES)
        self.assertIn("settings", VIEW_NAMES)
        self.assertIn("AI 地址", SETTINGS_FIELD_LABELS)
        self.assertIn("API Key", SETTINGS_FIELD_LABELS)

    def test_compact_window_uses_dense_status_summary(self):
        width, height = COMPACT_WINDOW_SIZE

        self.assertLessEqual(width, 320)
        self.assertLessEqual(height, 170)
        self.assertEqual(("C", "Δ", "BR"), MINI_METRIC_LABELS)

    def test_exit_app_disposes_tray_once_and_releases_reference(self):
        app = CommitDiaryDesktopApp.__new__(CommitDiaryDesktopApp)
        root = FakeRoot()
        tray = FakeTray()
        app.root = root
        app._tray = tray
        app._save_position = lambda: None

        app.exit_app()
        app.exit_app()

        self.assertEqual(1, tray.dispose_count)
        self.assertTrue(root.destroyed)
        self.assertIsNone(app._tray)


class FakeRoot:
    def __init__(self):
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


class FakeTray:
    def __init__(self):
        self.dispose_count = 0

    def dispose(self):
        self.dispose_count += 1


if __name__ == "__main__":
    unittest.main()
