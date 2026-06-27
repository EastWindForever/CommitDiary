import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.ai import AiDiaryRequest, OpenAiCompatibleDiaryEnhancer
from commitdiary.models import GitCommitEntry, GitSnapshot, GitWorkingTreeStatus


class AiEnhancerTests(unittest.TestCase):
    def test_build_payload_contains_summary_level_context(self):
        snapshot = GitSnapshot(
            "CommitDiary",
            r"D:\Code\work\CommitDiary",
            "main",
            datetime(2026, 6, 27, 19, 0, tzinfo=timezone.utc),
            [GitCommitEntry("abc123", "feat: add generator", "Edge", datetime.now(timezone.utc), ["src/app.py"])],
            GitWorkingTreeStatus(0, 0, 0, []),
        )
        request = AiDiaryRequest(snapshot=snapshot, draft_markdown="# 今日概览\n完成生成器")

        payload = OpenAiCompatibleDiaryEnhancer.build_payload(request, model="gpt-test")
        encoded = json.dumps(payload, ensure_ascii=False)

        self.assertIn("gpt-test", encoded)
        self.assertIn("CommitDiary", encoded)
        self.assertIn("main", encoded)
        self.assertIn("feat: add generator", encoded)
        self.assertIn("src/app.py", encoded)
        self.assertIn("完成生成器", encoded)


if __name__ == "__main__":
    unittest.main()
