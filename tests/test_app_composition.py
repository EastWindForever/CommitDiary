import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.app_composition import build_view_model
from commitdiary.view_model import CommitDiaryViewModel


class AppCompositionTests(unittest.TestCase):
    def test_build_view_model_returns_desktop_view_model(self):
        view_model = build_view_model()

        self.assertIsInstance(view_model, CommitDiaryViewModel)


if __name__ == "__main__":
    unittest.main()
