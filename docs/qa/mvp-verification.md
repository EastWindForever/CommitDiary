# CommitDiary MVP Verification

## 验证环境

| 项目 | 结果 |
|---|---|
| 工作区 | `D:\Code\work\CommitDiary` |
| 目标平台 | Windows |
| 实现路径 | Python 3.12 + Tkinter 标准库桌面应用 |
| 外部依赖 | 无 |
| .NET 状态 | 当前机器只有 .NET 6 runtime，没有 .NET SDK |

## 自动验证

| 命令 | 结果 |
|---|---|
| `python -m unittest discover -s tests` | 10 tests passed |
| `python -m compileall src run_commit_diary.py` | 编译检查通过 |
| `python run_commit_diary.py --smoke` | `desktop-smoke-ok` |

## PRD 验收映射

| PRD 验收项 | 当前证据 |
|---|---|
| 悬浮窗启动 | `--smoke` 能创建并销毁 Tkinter 桌面窗口 |
| 状态展示 | `CommitDiaryViewModelTests.test_refresh_updates_float_status` 覆盖仓库名、分支、提交数、变更数、最近提交 |
| 日记生成 | `DiaryGeneratorTests.test_generate_creates_markdown_with_overview_commits_and_todos` 覆盖 Markdown 日记 |
| AI 增强 | `AiEnhancerTests.test_build_payload_contains_summary_level_context` 覆盖 OpenAI-compatible 请求上下文 |
| 复制日报 | `desktop_app.copy_diary` 使用 Tkinter clipboard 写入最近日报文本 |
| 托盘常驻 | `WindowsTrayIcon` 使用 Windows `Shell_NotifyIconW` 注册托盘入口 |
| 本地持久化 | `StorageTests` 覆盖 settings/history JSON 读写 |
| 错误反馈 | `CommitDiaryViewModel.refresh` 和 `generate` 记录扫描失败、无效仓库、AI 失败状态 |

## 手工验证入口

```bash
python run_commit_diary.py
```

启动后建议手工检查：

| 动作 | 期望结果 |
|---|---|
| 拖动顶部栏 | 窗口跟随鼠标移动 |
| 点击设置 | 打开仓库路径和 AI 配置表单 |
| 选择 Git 仓库 | 窗口展示仓库名、分支、今日提交、变更数 |
| 点击生成 | 展开视图出现 Markdown 开发日记 |
| 点击复制 | 剪贴板写入日报文本 |
| 点击打开 | Explorer 打开当前仓库目录 |
| 点击隐藏 | 窗口隐藏，托盘入口可恢复显示 |

## 剩余风险

| 风险 | 说明 |
|---|---|
| 托盘行为需要真机确认 | `Shell_NotifyIconW` 依赖 Windows Explorer 托盘环境，自动测试只覆盖语法和组合 |
| AI 增强需要真实凭证 | 当前测试覆盖请求构造，未调用外部网络 |
| Git 工作区未初始化 | 当前目录 `git status` 返回不是 Git 仓库，无法提交变更 |
| WPF 计划已切换 | 机器缺少 .NET SDK，本轮改用 Python/Tkinter 实现 PRD 行为 |
