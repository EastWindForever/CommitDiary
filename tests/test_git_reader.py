import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.git_reader import GitCliSnapshotReader, ProcessResult


class FakeProcessRunner:
    def __init__(self):
        self.results = {}

    def returns(self, arguments, result):
        self.results[arguments] = result
        return self

    def run(self, arguments, cwd):
        return self.results[arguments]


class GitCliSnapshotReaderTests(unittest.TestCase):
    def test_read_maps_git_output_into_snapshot(self):
        runner = (
            FakeProcessRunner()
            .returns("rev-parse --show-toplevel", ProcessResult(0, r"D:\Code\work\CommitDiary", ""))
            .returns("rev-parse --abbrev-ref HEAD", ProcessResult(0, "main", ""))
            .returns(
                "log --since=midnight --name-only --pretty=format:%H%x1f%an%x1f%aI%x1f%s",
                ProcessResult(
                    0,
                    "abc123\x1fEdge\x1f2026-06-27T10:00:00+08:00\x1ffeat: add generator\n"
                    "src/app.py\n\n"
                    "def456\x1fEdge\x1f2026-06-27T11:00:00+08:00\x1ffix: polish copy\n"
                    "src/diary.py",
                    "",
                ),
            )
            .returns("status --porcelain", ProcessResult(0, " M src/app.py\nA  src/new.py\n?? notes.md", ""))
        )

        snapshot = GitCliSnapshotReader(runner).read(r"D:\Code\work\CommitDiary")

        self.assertEqual("CommitDiary", snapshot.repository_name)
        self.assertEqual("main", snapshot.branch_name)
        self.assertEqual(2, len(snapshot.today_commits))
        self.assertEqual(3, snapshot.working_tree.total_changes)
        self.assertEqual(["src/app.py"], snapshot.today_commits[0].changed_files)


if __name__ == "__main__":
    unittest.main()
