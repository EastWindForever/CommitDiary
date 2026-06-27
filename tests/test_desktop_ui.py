import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.desktop_app import PRIMARY_ACTION_LABELS, SETTINGS_FIELD_LABELS, VIEW_NAMES


class DesktopUiTests(unittest.TestCase):
    def test_primary_actions_include_repository_picker(self):
        self.assertIn("选择", PRIMARY_ACTION_LABELS)

    def test_main_window_owns_settings_controls(self):
        self.assertIn("dashboard", VIEW_NAMES)
        self.assertIn("settings", VIEW_NAMES)
        self.assertIn("AI 地址", SETTINGS_FIELD_LABELS)
        self.assertIn("API Key", SETTINGS_FIELD_LABELS)


if __name__ == "__main__":
    unittest.main()
