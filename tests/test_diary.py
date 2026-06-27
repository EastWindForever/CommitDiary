import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.diary import DiaryGenerator
from commitdiary.models import GitCommitEntry, GitSnapshot, GitWorkingTreeStatus


class DiaryGeneratorTests(unittest.TestCase):
    def test_generate_creates_markdown_with_overview_commits_and_todos(self):
        snapshot = GitSnapshot(
            repository_name="CommitDiary",
            repository_path=r"D:\Code\work\CommitDiary",
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

        draft = DiaryGenerator().generate(snapshot)

        self.assertIn("今日概览", draft.markdown)
        self.assertIn("feat: add diary generator", draft.markdown)
        self.assertIn("src/diary.py", draft.markdown)
        self.assertIn("待处理事项", draft.markdown)
        self.assertIn("今日完成", draft.copy_text)


if __name__ == "__main__":
    unittest.main()
