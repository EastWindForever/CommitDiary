from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import GitCommitEntry, GitSnapshot, GitWorkingTreeStatus


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


class SubprocessRunner:
    def run(self, arguments: str, cwd: str) -> ProcessResult:
        completed = subprocess.run(
            ["git", *arguments.split(" ")],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return ProcessResult(completed.returncode, completed.stdout.strip(), completed.stderr.strip())


class GitCliSnapshotReader:
    LOG_COMMAND = "log --since=midnight --name-only --pretty=format:%H%x1f%an%x1f%aI%x1f%s"

    def __init__(self, runner: SubprocessRunner | None = None):
        self._runner = runner or SubprocessRunner()

    def read(self, repository_path: str) -> GitSnapshot:
        root = self._run_git("rev-parse --show-toplevel", repository_path).stdout.strip()
        branch = self._run_git("rev-parse --abbrev-ref HEAD", root).stdout.strip()
        log_output = self._run_git(self.LOG_COMMAND, root).stdout
        status_output = self._run_git("status --porcelain", root).stdout
        commits = self._parse_log(log_output)
        working_tree = self._parse_status(status_output)
        return GitSnapshot(
            repository_name=Path(root).name,
            repository_path=root,
            branch_name=branch,
            captured_at=datetime.now(timezone.utc),
            today_commits=commits,
            working_tree=working_tree,
        )

    def _run_git(self, arguments: str, cwd: str) -> ProcessResult:
        result = self._runner.run(arguments, cwd)
        if result.returncode != 0:
            message = result.stderr or result.stdout or f"git {arguments} failed"
            raise RuntimeError(message)
        return result

    def _parse_log(self, output: str) -> list[GitCommitEntry]:
        commits: list[GitCommitEntry] = []
        current: GitCommitEntry | None = None
        files: list[str] = []

        def flush() -> None:
            nonlocal current, files
            if current is not None:
                commits.append(
                    GitCommitEntry(
                        hash=current.hash,
                        message=current.message,
                        author=current.author,
                        committed_at=current.committed_at,
                        changed_files=files.copy(),
                    )
                )
            current = None
            files = []

        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if "\x1f" in line:
                flush()
                parts = line.split("\x1f", 3)
                if len(parts) == 4:
                    committed_at = _parse_datetime(parts[2])
                    current = GitCommitEntry(parts[0], parts[3], parts[1], committed_at, [])
                continue
            if current is not None:
                files.append(line)
        flush()
        return commits

    def _parse_status(self, output: str) -> GitWorkingTreeStatus:
        modified = 0
        added = 0
        deleted = 0
        files: list[str] = []
        for raw_line in output.splitlines():
            if len(raw_line) < 3:
                continue
            code = raw_line[:2]
            path = raw_line[3:].strip()
            if not path:
                continue
            files.append(path)
            if "D" in code:
                deleted += 1
            elif "A" in code or code == "??":
                added += 1
            else:
                modified += 1
        return GitWorkingTreeStatus(modified, added, deleted, files)


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
