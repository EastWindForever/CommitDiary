# Git Commit Diary Desktop Float

Git Commit Diary 是一个 Windows 桌面悬浮小应用，用本地 Git 提交和工作区状态生成开发日记。

## 运行

```bash
python run_commit_diary.py
```

## 测试

```bash
python -m unittest discover -s tests
```

## 首版能力

| 能力 | 状态 |
|---|---|
| 悬浮小窗 | 已实现，支持置顶、拖拽、折叠和展开 |
| Git 状态读取 | 已实现，读取分支、今日提交、最近提交和未提交变更 |
| 本地日记生成 | 已实现，输出 Markdown 和复制版日报 |
| AI 增强 | 已实现 OpenAI-compatible 适配器，需要配置 API 信息 |
| 本地存储 | 已实现，配置和历史保存在 `%APPDATA%\CommitDiary` |
| 托盘 | 已实现 Windows 原生托盘兼容层 |
