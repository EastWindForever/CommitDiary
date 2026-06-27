from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from .models import GitCommitEntry, GitSnapshot


@dataclass(frozen=True)
class DiaryDraft:
    markdown: str
    copy_text: str


class CommitClassifier:
    TYPE_LABELS = {
        "feat": "功能开发",
        "fix": "问题修复",
        "refactor": "重构优化",
        "docs": "文档更新",
        "test": "测试完善",
        "chore": "工程维护",
    }

    def classify(self, commit: GitCommitEntry) -> str:
        prefix = commit.message.split(":", 1)[0].lower().strip()
        return self.TYPE_LABELS.get(prefix, "开发改动")


class DiaryGenerator:
    def __init__(self, classifier: CommitClassifier | None = None):
        self._classifier = classifier or CommitClassifier()

    def generate(self, snapshot: GitSnapshot) -> DiaryDraft:
        commit_count = len(snapshot.today_commits)
        change_count = snapshot.working_tree.total_changes
        affected = _affected_scopes(snapshot)
        lines = [
            f"# {snapshot.repository_name} 开发日记",
            "",
            "## 今日概览",
            f"- 当前分支：`{snapshot.branch_name}`",
            f"- 今日提交：{commit_count} 次",
            f"- 待提交变更：{change_count} 个文件",
            f"- 影响范围：{', '.join(affected) if affected else '暂无明确文件范围'}",
            "",
            "## 提交摘要",
        ]
        if snapshot.today_commits:
            for commit in snapshot.today_commits:
                label = self._classifier.classify(commit)
                short_hash = commit.hash[:7]
                lines.append(f"- [{label}] `{short_hash}` {commit.message}")
                for file_path in commit.changed_files[:8]:
                    lines.append(f"  - `{file_path}`")
        else:
            lines.append("- 今日暂无提交记录。")

        lines.extend(["", "## 影响范围"])
        if affected:
            lines.extend(f"- `{scope}`" for scope in affected)
        else:
            lines.append("- 暂无文件级影响范围。")

        lines.extend(["", "## 待处理事项"])
        if snapshot.working_tree.changed_files:
            lines.append(f"- 仍有 {change_count} 个未提交变更需要确认：")
            lines.extend(f"  - `{path}`" for path in snapshot.working_tree.changed_files[:10])
        else:
            lines.append("- 工作区当前没有未提交变更。")

        copy_text = _build_copy_text(snapshot, affected)
        lines.extend(["", "## 复制版日报", copy_text])
        return DiaryDraft(markdown="\n".join(lines).strip() + "\n", copy_text=copy_text)


def _affected_scopes(snapshot: GitSnapshot) -> list[str]:
    files: list[str] = []
    for commit in snapshot.today_commits:
        files.extend(commit.changed_files)
    files.extend(snapshot.working_tree.changed_files)
    scopes = []
    for file_path in files:
        path = PurePath(file_path)
        part = path.parts[0] if path.parts else file_path
        if part and part not in scopes:
            scopes.append(part)
    return scopes[:8]


def _build_copy_text(snapshot: GitSnapshot, affected: list[str]) -> str:
    commit_count = len(snapshot.today_commits)
    change_count = snapshot.working_tree.total_changes
    scope_text = "、".join(affected) if affected else "当前仓库"
    latest = snapshot.today_commits[0].message if snapshot.today_commits else "暂无提交"
    return (
        f"今日完成 {snapshot.repository_name}（{snapshot.branch_name}）开发整理，"
        f"产生 {commit_count} 次提交，主要涉及 {scope_text}。"
        f"最近提交：{latest}。当前还有 {change_count} 个未提交变更待确认。"
    )
