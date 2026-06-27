import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.models import GitCommitEntry, GitSnapshot, GitWorkingTreeStatus


class GitSnapshotTests(unittest.TestCase):
    def test_has_today_activity_when_commits_or_changes_exist(self):
        snapshot = GitSnapshot(
            repository_name="CommitDiary",
            repository_path=r"D:\Code\work\CommitDiary",
            branch_name="main",
            captured_at=datetime(2026, 6, 27, 19, 0, tzinfo=timezone.utc),
            today_commits=[
                GitCommitEntry(
                    hash="abc123",
                    message="feat: add generator",
                    author="Edge",
                    committed_at=datetime(2026, 6, 27, 10, 0, tzinfo=timezone.utc),
                    changed_files=["src/app.py"],
                )
            ],
            working_tree=GitWorkingTreeStatus(
                modified_count=2,
                added_count=1,
                deleted_count=0,
                changed_files=["src/app.py"],
            ),
        )

        self.assertTrue(snapshot.has_today_activity)
        self.assertEqual(3, snapshot.working_tree.total_changes)


if __name__ == "__main__":
    unittest.main()
