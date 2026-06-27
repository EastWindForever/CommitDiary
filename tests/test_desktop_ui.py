import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.desktop_app import PRIMARY_ACTION_LABELS


class DesktopUiTests(unittest.TestCase):
    def test_primary_actions_include_repository_picker(self):
        self.assertIn("选择", PRIMARY_ACTION_LABELS)


if __name__ == "__main__":
    unittest.main()
