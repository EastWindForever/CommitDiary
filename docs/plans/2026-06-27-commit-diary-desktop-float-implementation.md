# Commit Diary Desktop Float Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Windows native floating desktop app that turns local Git activity into a reusable development diary.

**Architecture:** Use a WPF/.NET 8 desktop shell for the floating window and tray integration. Keep Git collection, diary generation, AI enhancement, and storage in testable service layers with MVVM bindings in the app project.

**Tech Stack:** .NET 8, WPF, xUnit, CommunityToolkit.Mvvm, System.Text.Json, Windows clipboard and tray APIs, local Git CLI, OpenAI-compatible HTTP adapter.

---

## Current Context

| Item | State |
|---|---|
| Workspace | `D:\Code\work\CommitDiary` |
| PRD | `docs/plans/2026-06-27-commit-diary-desktop-float-prd.md` |
| Git state | Current directory is not initialized as a Git repository |
| Product target | Windows single-platform native floating app |
| First implementation strategy | WPF/.NET 8 native desktop app |

## Milestone 0: Project Bootstrap

### Task 1: Create Solution Skeleton

**Files:**
- Create: `CommitDiary.sln`
- Create: `src/CommitDiary.App/CommitDiary.App.csproj`
- Create: `src/CommitDiary.Core/CommitDiary.Core.csproj`
- Create: `tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj`

**Step 1: Create the .NET solution**

Run:

```bash
dotnet new sln -n CommitDiary
dotnet new wpf -n CommitDiary.App -o src/CommitDiary.App
dotnet new classlib -n CommitDiary.Core -o src/CommitDiary.Core
dotnet new xunit -n CommitDiary.Core.Tests -o tests/CommitDiary.Core.Tests
dotnet sln CommitDiary.sln add src/CommitDiary.App/CommitDiary.App.csproj src/CommitDiary.Core/CommitDiary.Core.csproj tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj
dotnet add src/CommitDiary.App/CommitDiary.App.csproj reference src/CommitDiary.Core/CommitDiary.Core.csproj
dotnet add tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj reference src/CommitDiary.Core/CommitDiary.Core.csproj
```

Expected: solution contains app, core, and test projects.

**Step 2: Add core packages**

Run:

```bash
dotnet add src/CommitDiary.App/CommitDiary.App.csproj package CommunityToolkit.Mvvm
dotnet add src/CommitDiary.App/CommitDiary.App.csproj package Hardcodet.NotifyIcon.Wpf
```

Expected: app project can use MVVM helpers and tray icon integration.

**Step 3: Verify bootstrap**

Run:

```bash
dotnet build CommitDiary.sln
dotnet test CommitDiary.sln
```

Expected: build and tests pass.

**Step 4: Commit**

Run after Git is initialized:

```bash
git add CommitDiary.sln src tests
git commit -m "chore: bootstrap desktop app solution"
```

## Milestone 1: Core Domain Model

### Task 2: Define Git Snapshot Models

**Files:**
- Create: `src/CommitDiary.Core/Git/GitSnapshot.cs`
- Create: `src/CommitDiary.Core/Git/GitCommitEntry.cs`
- Create: `src/CommitDiary.Core/Git/GitWorkingTreeStatus.cs`
- Test: `tests/CommitDiary.Core.Tests/Git/GitSnapshotTests.cs`

**Step 1: Write the failing test**

```csharp
using CommitDiary.Core.Git;

namespace CommitDiary.Core.Tests.Git;

public class GitSnapshotTests
{
    [Fact]
    public void HasTodayActivity_ReturnsTrue_WhenCommitsOrChangesExist()
    {
        var snapshot = new GitSnapshot(
            RepositoryName: "CommitDiary",
            RepositoryPath: @"D:\Code\work\CommitDiary",
            BranchName: "main",
            CapturedAt: new DateTimeOffset(2026, 6, 27, 19, 0, 0, TimeSpan.FromHours(8)),
            TodayCommits: [new GitCommitEntry("abc123", "feat: add generator", "Edge", DateTimeOffset.Now, ["src/App.cs"])],
            WorkingTree: new GitWorkingTreeStatus(2, 1, 0, ["src/App.cs"]));

        Assert.True(snapshot.HasTodayActivity);
    }
}
```

**Step 2: Run test to verify it fails**

Run:

```bash
dotnet test tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj --filter GitSnapshotTests
```

Expected: FAIL because the models do not exist yet.

**Step 3: Implement the models**

```csharp
namespace CommitDiary.Core.Git;

public sealed record GitCommitEntry(
    string Hash,
    string Message,
    string Author,
    DateTimeOffset CommittedAt,
    IReadOnlyList<string> ChangedFiles);
```

```csharp
namespace CommitDiary.Core.Git;

public sealed record GitWorkingTreeStatus(
    int ModifiedCount,
    int AddedCount,
    int DeletedCount,
    IReadOnlyList<string> ChangedFiles)
{
    public int TotalChanges => ModifiedCount + AddedCount + DeletedCount;
}
```

```csharp
namespace CommitDiary.Core.Git;

public sealed record GitSnapshot(
    string RepositoryName,
    string RepositoryPath,
    string BranchName,
    DateTimeOffset CapturedAt,
    IReadOnlyList<GitCommitEntry> TodayCommits,
    GitWorkingTreeStatus WorkingTree)
{
    public bool HasTodayActivity => TodayCommits.Count > 0 || WorkingTree.TotalChanges > 0;
}
```

**Step 4: Verify**

Run:

```bash
dotnet test tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj --filter GitSnapshotTests
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/CommitDiary.Core/Git tests/CommitDiary.Core.Tests/Git
git commit -m "feat: add git snapshot domain model"
```

## Milestone 2: Git Collection

### Task 3: Implement Git CLI Reader

**Files:**
- Create: `src/CommitDiary.Core/Git/IGitSnapshotReader.cs`
- Create: `src/CommitDiary.Core/Git/GitCliSnapshotReader.cs`
- Create: `src/CommitDiary.Core/System/IProcessRunner.cs`
- Create: `src/CommitDiary.Core/System/ProcessResult.cs`
- Test: `tests/CommitDiary.Core.Tests/Git/GitCliSnapshotReaderTests.cs`

**Step 1: Write tests for parsing**

```csharp
using CommitDiary.Core.Git;
using CommitDiary.Core.System;

namespace CommitDiary.Core.Tests.Git;

public class GitCliSnapshotReaderTests
{
    [Fact]
    public async Task ReadAsync_MapsGitOutputIntoSnapshot()
    {
        var runner = new FakeProcessRunner()
            .Returns("rev-parse --show-toplevel", new ProcessResult(0, @"D:\Code\work\CommitDiary", ""))
            .Returns("rev-parse --abbrev-ref HEAD", new ProcessResult(0, "main", ""))
            .Returns("log --since=midnight --name-only --pretty=format:%H%x1f%an%x1f%aI%x1f%s", new ProcessResult(0,
                "abc123\u001fEdge\u001f2026-06-27T10:00:00+08:00\u001ffeat: add generator\nsrc/App.cs", ""))
            .Returns("status --porcelain", new ProcessResult(0, " M src/App.cs\nA  src/New.cs", ""));

        var reader = new GitCliSnapshotReader(runner);

        var snapshot = await reader.ReadAsync(@"D:\Code\work\CommitDiary", CancellationToken.None);

        Assert.Equal("CommitDiary", snapshot.RepositoryName);
        Assert.Equal("main", snapshot.BranchName);
        Assert.Single(snapshot.TodayCommits);
        Assert.Equal(2, snapshot.WorkingTree.TotalChanges);
    }

    private sealed class FakeProcessRunner : IProcessRunner
    {
        private readonly Dictionary<string, ProcessResult> _results = new();

        public FakeProcessRunner Returns(string arguments, ProcessResult result)
        {
            _results[arguments] = result;
            return this;
        }

        public Task<ProcessResult> RunAsync(string fileName, string arguments, string workingDirectory, CancellationToken cancellationToken)
        {
            return Task.FromResult(_results[arguments]);
        }
    }
}
```

**Step 2: Run the failing test**

Run:

```bash
dotnet test tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj --filter GitCliSnapshotReaderTests
```

Expected: FAIL because reader and process abstractions do not exist yet.

**Step 3: Implement process abstraction**

Create `ProcessResult` and `IProcessRunner`, then implement `GitCliSnapshotReader` with these commands:

| Command | Purpose |
|---|---|
| `rev-parse --show-toplevel` | Resolve repository root |
| `rev-parse --abbrev-ref HEAD` | Resolve branch |
| `log --since=midnight --name-only --pretty=format:%H%x1f%an%x1f%aI%x1f%s` | Read today's commits and files |
| `status --porcelain` | Read working tree changes |

**Step 4: Verify**

Run:

```bash
dotnet test tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj --filter GitCliSnapshotReaderTests
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/CommitDiary.Core/Git src/CommitDiary.Core/System tests/CommitDiary.Core.Tests/Git
git commit -m "feat: read git snapshot from local repository"
```

## Milestone 3: Diary Generation

### Task 4: Generate Markdown Diary Drafts

**Files:**
- Create: `src/CommitDiary.Core/Diary/DiaryDraft.cs`
- Create: `src/CommitDiary.Core/Diary/DiaryGenerator.cs`
- Create: `src/CommitDiary.Core/Diary/CommitClassifier.cs`
- Test: `tests/CommitDiary.Core.Tests/Diary/DiaryGeneratorTests.cs`

**Step 1: Write the failing test**

```csharp
using CommitDiary.Core.Diary;
using CommitDiary.Core.Git;

namespace CommitDiary.Core.Tests.Diary;

public class DiaryGeneratorTests
{
    [Fact]
    public void Generate_CreatesMarkdownWithOverviewCommitsAndTodos()
    {
        var snapshot = new GitSnapshot(
            "CommitDiary",
            @"D:\Code\work\CommitDiary",
            "main",
            DateTimeOffset.Now,
            [new GitCommitEntry("abc123", "feat: add diary generator", "Edge", DateTimeOffset.Now, ["src/Diary/DiaryGenerator.cs"])],
            new GitWorkingTreeStatus(1, 0, 0, ["src/App.xaml"]));

        var draft = new DiaryGenerator().Generate(snapshot);

        Assert.Contains("今日概览", draft.Markdown);
        Assert.Contains("feat: add diary generator", draft.Markdown);
        Assert.Contains("src/Diary/DiaryGenerator.cs", draft.Markdown);
        Assert.Contains("待处理事项", draft.Markdown);
    }
}
```

**Step 2: Verify failure**

Run:

```bash
dotnet test tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj --filter DiaryGeneratorTests
```

Expected: FAIL because diary classes do not exist yet.

**Step 3: Implement generator**

Generator output sections:

| Section | Content |
|---|---|
| 今日概览 | Commit count, branch, activity summary |
| 提交摘要 | Commit hash, type, message, changed files |
| 影响范围 | Distinct top-level folders and file extensions |
| 待处理事项 | Working tree changed files |
| 复制版日报 | Short paragraph for copy action |

**Step 4: Verify**

Run:

```bash
dotnet test tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj --filter DiaryGeneratorTests
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/CommitDiary.Core/Diary tests/CommitDiary.Core.Tests/Diary
git commit -m "feat: generate markdown diary draft"
```

## Milestone 4: AI Enhancement

### Task 5: Add AI Enhancement Port

**Files:**
- Create: `src/CommitDiary.Core/Ai/IAiDiaryEnhancer.cs`
- Create: `src/CommitDiary.Core/Ai/AiDiaryRequest.cs`
- Create: `src/CommitDiary.Core/Ai/AiDiaryResult.cs`
- Create: `src/CommitDiary.Core/Ai/OpenAiCompatibleDiaryEnhancer.cs`
- Test: `tests/CommitDiary.Core.Tests/Ai/OpenAiCompatibleDiaryEnhancerTests.cs`

**Step 1: Write tests around request shaping**

Test that the enhancer sends summary-level context containing:

| Field | Source |
|---|---|
| Repository | `GitSnapshot.RepositoryName` |
| Branch | `GitSnapshot.BranchName` |
| Commits | Commit messages and changed file paths |
| Draft | Local Markdown draft |

**Step 2: Implement interface**

```csharp
namespace CommitDiary.Core.Ai;

public interface IAiDiaryEnhancer
{
    Task<AiDiaryResult> EnhanceAsync(AiDiaryRequest request, CancellationToken cancellationToken);
}
```

**Step 3: Implement HTTP adapter**

Use `HttpClient` and configuration values:

| Setting | Purpose |
|---|---|
| `Ai:BaseUrl` | OpenAI-compatible endpoint |
| `Ai:ApiKey` | API key |
| `Ai:Model` | Model name |
| `Ai:Enabled` | Enable enhanced diary generation |

**Step 4: Verify**

Run:

```bash
dotnet test tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj --filter OpenAiCompatibleDiaryEnhancerTests
```

Expected: PASS with a fake HTTP handler.

**Step 5: Commit**

```bash
git add src/CommitDiary.Core/Ai tests/CommitDiary.Core.Tests/Ai
git commit -m "feat: add ai diary enhancement adapter"
```

## Milestone 5: Local Storage

### Task 6: Persist Settings and Diary History

**Files:**
- Create: `src/CommitDiary.Core/Storage/AppSettings.cs`
- Create: `src/CommitDiary.Core/Storage/DiaryHistoryEntry.cs`
- Create: `src/CommitDiary.Core/Storage/JsonSettingsStore.cs`
- Create: `src/CommitDiary.Core/Storage/JsonDiaryHistoryStore.cs`
- Test: `tests/CommitDiary.Core.Tests/Storage/JsonSettingsStoreTests.cs`

**Step 1: Write persistence tests**

Test cases:

| Case | Expected |
|---|---|
| Save settings | JSON file contains repository path and window position |
| Load missing settings | Returns default settings |
| Save history | Latest diary entry is persisted |

**Step 2: Implement stores**

Use app data path:

```text
%APPDATA%\CommitDiary\
```

Files:

| File | Content |
|---|---|
| `settings.json` | Repository path, window position, AI settings |
| `history.json` | Diary history entries |

**Step 3: Verify**

Run:

```bash
dotnet test tests/CommitDiary.Core.Tests/CommitDiary.Core.Tests.csproj --filter Storage
```

Expected: PASS.

**Step 4: Commit**

```bash
git add src/CommitDiary.Core/Storage tests/CommitDiary.Core.Tests/Storage
git commit -m "feat: persist settings and diary history"
```

## Milestone 6: WPF Floating Shell

### Task 7: Build Floating Window UI

**Files:**
- Modify: `src/CommitDiary.App/MainWindow.xaml`
- Modify: `src/CommitDiary.App/MainWindow.xaml.cs`
- Create: `src/CommitDiary.App/ViewModels/FloatWindowViewModel.cs`
- Create: `src/CommitDiary.App/Views/DiaryDetailPanel.xaml`

**Step 1: Create view model state**

Expose these properties:

| Property | Purpose |
|---|---|
| `RepositoryName` | Header title |
| `BranchName` | Header branch |
| `TodayCommitCount` | Core metric |
| `WorkingTreeChangeCount` | Core metric |
| `LatestCommitMessage` | Recent commit line |
| `StatusText` | Generated, enhancing, copied, scan failed |
| `DiaryMarkdown` | Detail preview |
| `IsExpanded` | Fold or expanded state |

**Step 2: Create commands**

| Command | Action |
|---|---|
| `RefreshCommand` | Refresh Git snapshot |
| `GenerateCommand` | Generate local draft and optional AI enhancement |
| `CopyCommand` | Copy latest diary text |
| `ToggleExpandedCommand` | Fold or expand the detail panel |
| `OpenRepositoryCommand` | Open repository folder |

**Step 3: Implement floating behavior**

Main window requirements:

| Behavior | Requirement |
|---|---|
| Always-on-top | `Topmost = true` |
| No standard chrome | Custom compact chrome |
| Drag support | Header drag moves window |
| Position restore | Load and save window coordinates |
| Compact size | Default width around 320 px |

**Step 4: Manual verification**

Run:

```bash
dotnet run --project src/CommitDiary.App/CommitDiary.App.csproj
```

Expected: Windows desktop shows a draggable topmost floating window.

**Step 5: Commit**

```bash
git add src/CommitDiary.App
git commit -m "feat: add floating desktop window"
```

## Milestone 7: Tray and App Commands

### Task 8: Add Tray Menu and Clipboard Integration

**Files:**
- Create: `src/CommitDiary.App/Services/TrayService.cs`
- Create: `src/CommitDiary.App/Services/ClipboardService.cs`
- Create: `src/CommitDiary.App/Services/FolderOpenService.cs`
- Modify: `src/CommitDiary.App/App.xaml.cs`

**Step 1: Add tray menu**

Menu items:

| Item | Action |
|---|---|
| Show | Show floating window |
| Hide | Hide floating window |
| Select Repository | Open folder picker |
| Settings | Open settings panel |
| Exit | Shutdown app |

**Step 2: Add clipboard service**

Use WPF `Clipboard.SetText` through an injectable service.

**Step 3: Add folder opening service**

Use `ProcessStartInfo` with `UseShellExecute = true` for repository folders.

**Step 4: Verify**

Manual checks:

| Check | Expected |
|---|---|
| Hide from tray | Window disappears |
| Show from tray | Window reappears |
| Copy diary | Clipboard contains latest diary text |
| Open repository | Explorer opens repository folder |

**Step 5: Commit**

```bash
git add src/CommitDiary.App/Services src/CommitDiary.App/App.xaml.cs
git commit -m "feat: add tray menu and desktop integrations"
```

## Milestone 8: End-to-End Composition

### Task 9: Wire Services Into App Startup

**Files:**
- Modify: `src/CommitDiary.App/App.xaml.cs`
- Modify: `src/CommitDiary.App/ViewModels/FloatWindowViewModel.cs`
- Create: `src/CommitDiary.App/Composition/AppCompositionRoot.cs`

**Step 1: Add composition root**

Register:

| Service | Implementation |
|---|---|
| `IProcessRunner` | Real process runner |
| `IGitSnapshotReader` | Git CLI reader |
| `DiaryGenerator` | Local diary generator |
| `IAiDiaryEnhancer` | OpenAI-compatible enhancer or disabled enhancer |
| Settings store | JSON settings store |
| History store | JSON diary history store |
| Desktop services | Tray, clipboard, folder opener |

**Step 2: Wire view model**

The view model should:

| Event | Behavior |
|---|---|
| Startup | Load settings and restore state |
| Refresh | Read Git snapshot and update status |
| Generate | Generate draft, optionally enhance, save history |
| Copy | Copy latest generated text |
| Close | Save window position and hide to tray |

**Step 3: Run full verification**

Run:

```bash
dotnet build CommitDiary.sln
dotnet test CommitDiary.sln
dotnet run --project src/CommitDiary.App/CommitDiary.App.csproj
```

Expected: app builds, tests pass, and MVP can run locally.

**Step 4: Commit**

```bash
git add src tests
git commit -m "feat: wire commit diary desktop workflow"
```

## Milestone 9: MVP Verification

### Task 10: Validate PRD Acceptance Criteria

**Files:**
- Create: `docs/qa/mvp-verification.md`

**Step 1: Create verification checklist**

Include:

| Criterion | Verification |
|---|---|
| Floating startup | Screenshot or manual note |
| Git status | Test repository path and displayed values |
| Diary draft | Generated Markdown sample |
| AI enhancement | Configured endpoint test result |
| Copy action | Clipboard content sample |
| Tray behavior | Show, hide, settings, exit notes |
| Persistence | Restart and restored state note |
| Error feedback | Invalid repository path note |

**Step 2: Run verification commands**

```bash
dotnet build CommitDiary.sln
dotnet test CommitDiary.sln
```

Expected: build and tests pass.

**Step 3: Manual verification**

Use a real local Git repository with at least one commit today.

Expected:

| Action | Result |
|---|---|
| Select repo | Window shows repo and branch |
| Refresh | Counts update |
| Generate | Markdown diary appears |
| Copy | Diary text appears in clipboard |
| Hide tray | Window hides and app remains active |
| Exit tray | App exits |

**Step 4: Commit**

```bash
git add docs/qa/mvp-verification.md
git commit -m "test: document mvp verification"
```

## Execution Notes

| Topic | Decision |
|---|---|
| Desktop framework | WPF/.NET 8 for native Windows floating window behavior |
| Git access | Git CLI through process abstraction for straightforward MVP behavior |
| AI access | OpenAI-compatible adapter behind `IAiDiaryEnhancer` |
| Offline behavior | Local rule-based diary generator remains the baseline path |
| Testing focus | Core Git parsing, diary generation, AI request shaping, storage |
| Manual QA focus | Floating window, tray, clipboard, folder opening, persistence |

## Completion Evidence

| Evidence | Source |
|---|---|
| PRD exists | `docs/plans/2026-06-27-commit-diary-desktop-float-prd.md` |
| Plan exists | `docs/plans/2026-06-27-commit-diary-desktop-float-implementation.md` |
| Build status | `dotnet build CommitDiary.sln` |
| Test status | `dotnet test CommitDiary.sln` |
| Manual app status | `dotnet run --project src/CommitDiary.App/CommitDiary.App.csproj` |

Plan complete and saved to `docs/plans/2026-06-27-commit-diary-desktop-float-implementation.md`. Two execution options:

1. Subagent-Driven (this session) - dispatch fresh subagent per task, review between tasks, fast iteration.
2. Parallel Session (separate) - open new session with executing-plans, batch execution with checkpoints.
