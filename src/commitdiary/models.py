from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class GitCommitEntry:
    hash: str
    message: str
    author: str
    committed_at: datetime
    changed_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GitWorkingTreeStatus:
    modified_count: int
    added_count: int
    deleted_count: int
    changed_files: list[str] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return self.modified_count + self.added_count + self.deleted_count


@dataclass(frozen=True)
class GitSnapshot:
    repository_name: str
    repository_path: str
    branch_name: str
    captured_at: datetime
    today_commits: list[GitCommitEntry] = field(default_factory=list)
    working_tree: GitWorkingTreeStatus = field(
        default_factory=lambda: GitWorkingTreeStatus(0, 0, 0, [])
    )

    @property
    def has_today_activity(self) -> bool:
        return bool(self.today_commits) or self.working_tree.total_changes > 0
