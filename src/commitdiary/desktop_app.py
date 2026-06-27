from __future__ import annotations

import os
import platform
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox

from .app_composition import build_view_model
from .diary import DiaryGenerator
from .git_reader import GitCliSnapshotReader
from .storage import AppSettings, JsonDiaryHistoryStore, JsonSettingsStore
from .tray import WindowsTrayIcon
from .view_model import CommitDiaryViewModel


PRIMARY_ACTION_LABELS = ("刷新", "选择", "生成", "复制", "打开", "设置")


class CommitDiaryDesktopApp:
    def __init__(self, root: tk.Tk, view_model: CommitDiaryViewModel, enable_tray: bool = True):
        self.root = root
        self.vm = view_model
        self._drag_start: tuple[int, int] | None = None
        self._tray: WindowsTrayIcon | None = None
        self._build_window()
        self._bind_events()
        self._restore_geometry()
        self._refresh_labels()
        if enable_tray and platform.system() == "Windows":
            self._tray = WindowsTrayIcon(
                root=self.root,
                on_show=self.show,
                on_hide=self.hide,
                on_select_repository=self.select_repository,
                on_settings=self.open_settings,
                on_exit=self.exit_app,
            )

    def run(self) -> None:
        if self.vm.settings.repository_path:
            self._run_background(self._refresh_repository)
        self.root.mainloop()

    def _build_window(self) -> None:
        self.root.title("CommitDiary")
        self.root.configure(bg="#101418")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.minsize(320, 170)

        self.container = tk.Frame(self.root, bg="#101418", bd=1, relief="solid")
        self.container.pack(fill="both", expand=True)

        self.header = tk.Frame(self.container, bg="#151b22", height=38)
        self.header.pack(fill="x")
        self.title_label = tk.Label(
            self.header,
            text="CommitDiary · -",
            bg="#151b22",
            fg="#f4f7fb",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )
        self.title_label.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        self.collapse_button = tk.Button(
            self.header,
            text="▾",
            width=3,
            command=self.toggle_expanded,
            bg="#1f2933",
            fg="#f4f7fb",
            relief="flat",
        )
        self.collapse_button.pack(side="right", padx=(0, 6), pady=6)
        self.close_button = tk.Button(
            self.header,
            text="×",
            width=3,
            command=self.hide,
            bg="#1f2933",
            fg="#f4f7fb",
            relief="flat",
        )
        self.close_button.pack(side="right", padx=(0, 6), pady=6)

        self.body = tk.Frame(self.container, bg="#101418")
        self.body.pack(fill="both", expand=True, padx=12, pady=10)
        self.metric_label = tk.Label(
            self.body,
            text="今日 0 commits · 0 changes",
            bg="#101418",
            fg="#d8dee9",
            anchor="w",
            font=("Segoe UI", 10),
        )
        self.metric_label.pack(fill="x")
        self.latest_label = tk.Label(
            self.body,
            text="请选择 Git 仓库",
            bg="#101418",
            fg="#9fb0c3",
            anchor="w",
            justify="left",
            wraplength=300,
            font=("Segoe UI", 9),
        )
        self.latest_label.pack(fill="x", pady=(8, 0))
        self.status_label = tk.Label(
            self.body,
            text="待选择仓库",
            bg="#101418",
            fg="#7dd3fc",
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.status_label.pack(fill="x", pady=(8, 0))

        self.button_row = tk.Frame(self.body, bg="#101418")
        self.button_row.pack(fill="x", pady=(10, 0))
        self._button("刷新", self.refresh).pack(side="left", padx=(0, 5))
        self._button("选择", self.select_repository).pack(side="left", padx=(0, 5))
        self._button("生成", self.generate).pack(side="left", padx=(0, 5))
        self._button("复制", self.copy_diary).pack(side="left", padx=(0, 5))
        self._button("打开", self.open_repository).pack(side="left", padx=(0, 5))
        self._button("设置", self.open_settings).pack(side="left")

        self.detail_frame = tk.Frame(self.body, bg="#101418")
        self.diary_text = tk.Text(
            self.detail_frame,
            height=12,
            bg="#0b0f14",
            fg="#e5edf5",
            insertbackground="#e5edf5",
            relief="flat",
            wrap="word",
            font=("Consolas", 9),
        )
        self.diary_text.pack(fill="both", expand=True, pady=(10, 0))

    def _button(self, text: str, command) -> tk.Button:
        return tk.Button(
            self.button_row,
            text=text,
            command=command,
            bg="#243241",
            fg="#f4f7fb",
            activebackground="#2d4052",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=4,
            font=("Segoe UI", 9),
        )

    def _bind_events(self) -> None:
        self.header.bind("<ButtonPress-1>", self._start_drag)
        self.header.bind("<B1-Motion>", self._drag)
        self.title_label.bind("<ButtonPress-1>", self._start_drag)
        self.title_label.bind("<B1-Motion>", self._drag)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

    def _restore_geometry(self) -> None:
        settings = self.vm.settings
        self.root.geometry(
            f"{settings.window_width}x{settings.window_height}+{settings.window_x}+{settings.window_y}"
        )

    def _start_drag(self, event) -> None:
        self._drag_start = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def _drag(self, event) -> None:
        if self._drag_start is None:
            return
        x_offset, y_offset = self._drag_start
        self.root.geometry(f"+{event.x_root - x_offset}+{event.y_root - y_offset}")

    def refresh(self) -> None:
        self._run_background(self._refresh_repository)

    def generate(self) -> None:
        self.status_label.config(text="生成中...")
        self._run_background(self._generate_diary)

    def copy_diary(self) -> None:
        text = self.vm.copy_text or self.vm.diary_markdown
        if not text:
            self.vm.status_text = "暂无可复制日记"
            self._refresh_labels()
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.vm.status_text = "已复制日报"
        self._refresh_labels()

    def toggle_expanded(self) -> None:
        self.vm.toggle_expanded()
        if self.vm.is_expanded:
            self.detail_frame.pack(fill="both", expand=True)
            self.collapse_button.config(text="▴")
            self.root.geometry(f"520x560+{self.root.winfo_x()}+{self.root.winfo_y()}")
        else:
            self.detail_frame.pack_forget()
            self.collapse_button.config(text="▾")
            self.root.geometry(f"340x220+{self.root.winfo_x()}+{self.root.winfo_y()}")
        self._save_position()

    def select_repository(self) -> None:
        path = filedialog.askdirectory(title="选择 Git 仓库")
        if path:
            self._run_background(lambda: self._refresh_repository(path))

    def open_repository(self) -> None:
        path = self.vm.settings.repository_path
        if not path:
            self.vm.status_text = "请先选择仓库"
            self._refresh_labels()
            return
        try:
            open_path(path)
            self.vm.status_text = "已打开仓库目录"
        except Exception as exc:
            self.vm.status_text = f"打开仓库失败：{exc}"
        self._refresh_labels()

    def open_settings(self) -> None:
        settings = self.vm.settings
        dialog = tk.Toplevel(self.root)
        dialog.title("CommitDiary 设置")
        dialog.configure(bg="#101418")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        repo_var = tk.StringVar(value=settings.repository_path)
        enabled_var = tk.BooleanVar(value=settings.ai_enabled)
        base_url_var = tk.StringVar(value=settings.ai_base_url)
        model_var = tk.StringVar(value=settings.ai_model)
        api_key_var = tk.StringVar(value=settings.ai_api_key)

        def entry_row(label: str, variable: tk.StringVar, show: str | None = None) -> None:
            frame = tk.Frame(dialog, bg="#101418")
            frame.pack(fill="x", padx=14, pady=6)
            tk.Label(frame, text=label, bg="#101418", fg="#d8dee9", width=10, anchor="w").pack(side="left")
            tk.Entry(frame, textvariable=variable, width=42, show=show).pack(side="left", fill="x", expand=True)

        repo_frame = tk.Frame(dialog, bg="#101418")
        repo_frame.pack(fill="x", padx=14, pady=6)
        tk.Label(repo_frame, text="仓库路径", bg="#101418", fg="#d8dee9", width=10, anchor="w").pack(side="left")
        tk.Entry(repo_frame, textvariable=repo_var, width=34).pack(side="left", fill="x", expand=True)
        tk.Button(
            repo_frame,
            text="浏览",
            command=lambda: self._browse_repository(repo_var),
            bg="#243241",
            fg="#f4f7fb",
            relief="flat",
        ).pack(side="left", padx=(6, 0))
        entry_row("AI 地址", base_url_var)
        entry_row("AI 模型", model_var)
        entry_row("API Key", api_key_var, show="*")
        check = tk.Checkbutton(
            dialog,
            text="启用 AI 增强",
            variable=enabled_var,
            bg="#101418",
            fg="#d8dee9",
            selectcolor="#101418",
            activebackground="#101418",
            activeforeground="#ffffff",
        )
        check.pack(anchor="w", padx=14, pady=6)

        button_row = tk.Frame(dialog, bg="#101418")
        button_row.pack(fill="x", padx=14, pady=12)

        def save() -> None:
            self.vm.update_settings(
                replace(
                    self.vm.settings,
                    repository_path=repo_var.get().strip(),
                    ai_enabled=enabled_var.get(),
                    ai_base_url=base_url_var.get().strip() or "https://api.openai.com/v1",
                    ai_model=model_var.get().strip() or "gpt-4.1-mini",
                    ai_api_key=api_key_var.get().strip(),
                )
            )
            self.vm.status_text = "设置已保存"
            self._refresh_labels()
            dialog.destroy()

        tk.Button(button_row, text="保存", command=save, bg="#243241", fg="#f4f7fb", relief="flat").pack(
            side="right", padx=(6, 0)
        )
        tk.Button(button_row, text="取消", command=dialog.destroy, bg="#1f2933", fg="#f4f7fb", relief="flat").pack(
            side="right"
        )

    def _browse_repository(self, target: tk.StringVar) -> None:
        path = filedialog.askdirectory(title="选择 Git 仓库")
        if path:
            target.set(path)

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)

    def hide(self) -> None:
        self._save_position()
        self.root.withdraw()

    def exit_app(self) -> None:
        self._save_position()
        if self._tray:
            self._tray.dispose()
        self.root.destroy()

    def _refresh_repository(self, path: str | None = None) -> None:
        self.vm.refresh(path)
        self.root.after(0, self._refresh_labels)

    def _generate_diary(self) -> None:
        self.vm.generate()
        self.root.after(0, self._refresh_labels)

    def _refresh_labels(self) -> None:
        self.title_label.config(text=f"{self.vm.repository_name} · {self.vm.branch_name}")
        self.metric_label.config(
            text=f"今日 {self.vm.today_commit_count} commits · {self.vm.working_tree_change_count} changes"
        )
        self.latest_label.config(text=f"最近提交：{self.vm.latest_commit_message}")
        self.status_label.config(text=self.vm.status_text)
        self.diary_text.delete("1.0", tk.END)
        self.diary_text.insert("1.0", self.vm.diary_markdown)

    def _run_background(self, target) -> None:
        thread = threading.Thread(target=target, daemon=True)
        thread.start()

    def _save_position(self) -> None:
        self.vm.update_window_position(
            self.root.winfo_x(),
            self.root.winfo_y(),
            self.root.winfo_width(),
            self.root.winfo_height(),
        )


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if "--smoke" in argv:
        smoke()
        print("desktop-smoke-ok")
        return
    if "--tray-smoke" in argv:
        smoke(enable_tray=True)
        print("tray-smoke-ok")
        return
    root = tk.Tk()
    app = CommitDiaryDesktopApp(root, build_view_model())
    app.run()


def smoke(enable_tray: bool = False) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)
        settings_store = JsonSettingsStore(data_dir / "settings.json")
        history_store = JsonDiaryHistoryStore(data_dir / "history.json")
        view_model = CommitDiaryViewModel(
            settings=AppSettings(),
            reader=GitCliSnapshotReader(),
            generator=DiaryGenerator(),
            history_store=history_store,
            settings_store=settings_store,
        )
        root = tk.Tk()
        root.withdraw()
        app = CommitDiaryDesktopApp(root, view_model, enable_tray=enable_tray)
        root.after(1000, app.exit_app)
        root.mainloop()


def open_path(path: str) -> None:
    if platform.system() == "Windows":
        os.startfile(path)
    else:
        subprocess.Popen(["open", path])
