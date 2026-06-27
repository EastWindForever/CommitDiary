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
VIEW_NAMES = ("dashboard", "settings")
SETTINGS_FIELD_LABELS = ("仓库路径", "AI 地址", "AI 模型", "API Key")

COLORS = {
    "bg": "#0F172A",
    "surface": "#111827",
    "surface_alt": "#1E293B",
    "line": "#334155",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "subtle": "#CBD5E1",
    "accent": "#22C55E",
    "accent_dark": "#15803D",
    "info": "#38BDF8",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}


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
        self.root.configure(bg=COLORS["bg"])
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.minsize(360, 260)

        self.container = tk.Frame(
            self.root,
            bg=COLORS["bg"],
            highlightthickness=1,
            highlightbackground=COLORS["line"],
            highlightcolor=COLORS["line"],
        )
        self.container.pack(fill="both", expand=True)

        self.header = tk.Frame(self.container, bg=COLORS["surface"], height=46)
        self.header.pack(fill="x", padx=1, pady=1)
        self.title_label = tk.Label(
            self.header,
            text="CommitDiary · -",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            anchor="w",
            font=("Segoe UI", 11, "bold"),
        )
        self.title_label.pack(side="left", fill="x", expand=True, padx=14, pady=10)
        self.collapse_button = tk.Button(
            self.header,
            text="▾",
            width=3,
            command=self.toggle_expanded,
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            activebackground=COLORS["line"],
            activeforeground=COLORS["text"],
            relief="flat",
            bd=0,
            font=("Segoe UI", 10, "bold"),
        )
        self.collapse_button.pack(side="right", padx=(0, 6), pady=7)
        self.close_button = tk.Button(
            self.header,
            text="×",
            width=3,
            command=self.hide,
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            activebackground=COLORS["danger"],
            activeforeground=COLORS["text"],
            relief="flat",
            bd=0,
            font=("Segoe UI", 10, "bold"),
        )
        self.close_button.pack(side="right", padx=(0, 8), pady=7)

        self.content_frame = tk.Frame(self.container, bg=COLORS["bg"])
        self.content_frame.pack(fill="both", expand=True, padx=12, pady=(10, 12))
        self._render_current_view()

    def _button(self, text: str, command, parent: tk.Widget | None = None, variant: str = "secondary") -> tk.Button:
        parent = parent or self.button_row
        if variant == "primary":
            bg = COLORS["accent"]
            fg = "#052E16"
            active_bg = "#86EFAC"
        else:
            bg = COLORS["surface_alt"]
            fg = COLORS["text"]
            active_bg = COLORS["line"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            font=("Segoe UI", 9, "bold" if variant == "primary" else "normal"),
            cursor="hand2",
        )

    def _render_current_view(self) -> None:
        for child in self.content_frame.winfo_children():
            child.destroy()
        if self.vm.current_view == "settings":
            self._show_settings_view()
        else:
            self._show_dashboard_view()

    def _show_dashboard_view(self) -> None:
        self.collapse_button.config(
            text="▴" if self.vm.is_expanded else "▾",
            command=self.toggle_expanded,
        )
        hero = tk.Frame(self.content_frame, bg=COLORS["surface"])
        hero.pack(fill="x")

        status_color = self._status_color()
        self.status_label = tk.Label(
            hero,
            text=self.vm.status_text,
            bg=COLORS["surface"],
            fg=status_color,
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        )
        self.status_label.pack(fill="x", padx=12, pady=(10, 0))

        self.latest_label = tk.Label(
            hero,
            text=f"最近提交：{self.vm.latest_commit_message}",
            bg=COLORS["surface"],
            fg=COLORS["subtle"],
            anchor="w",
            justify="left",
            wraplength=460,
            font=("Segoe UI", 9),
        )
        self.latest_label.pack(fill="x", padx=12, pady=(6, 10))

        metrics = tk.Frame(self.content_frame, bg=COLORS["bg"])
        metrics.pack(fill="x", pady=(10, 0))
        self._metric_card(metrics, "Commits", str(self.vm.today_commit_count), COLORS["accent"]).pack(
            side="left", fill="x", expand=True, padx=(0, 6)
        )
        self._metric_card(metrics, "Changes", str(self.vm.working_tree_change_count), COLORS["warning"]).pack(
            side="left", fill="x", expand=True, padx=(0, 6)
        )
        self._metric_card(metrics, "Branch", self.vm.branch_name, COLORS["info"]).pack(
            side="left", fill="x", expand=True
        )

        self.button_row = tk.Frame(self.content_frame, bg=COLORS["bg"])
        self.button_row.pack(fill="x", pady=(12, 0))
        self._button("刷新", self.refresh).pack(side="left", padx=(0, 6))
        self._button("选择", self.select_repository).pack(side="left", padx=(0, 6))
        self._button("生成", self.generate, variant="primary").pack(side="left", padx=(0, 6))
        self._button("复制", self.copy_diary).pack(side="left", padx=(0, 6))
        self._button("打开", self.open_repository).pack(side="left", padx=(0, 6))
        self._button("设置", self.open_settings).pack(side="left")

        if self.vm.is_expanded:
            self.detail_frame = tk.Frame(
                self.content_frame,
                bg=COLORS["surface"],
                highlightthickness=1,
                highlightbackground=COLORS["line"],
            )
            self.detail_frame.pack(fill="both", expand=True, pady=(12, 0))
            tk.Label(
                self.detail_frame,
                text="开发日记预览",
                bg=COLORS["surface"],
                fg=COLORS["text"],
                anchor="w",
                font=("Segoe UI", 9, "bold"),
            ).pack(fill="x", padx=10, pady=(8, 0))
            self.diary_text = tk.Text(
                self.detail_frame,
                height=12,
                bg="#020617",
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat",
                wrap="word",
                font=("Consolas", 9),
                bd=0,
                padx=10,
                pady=8,
            )
            self.diary_text.pack(fill="both", expand=True, padx=10, pady=(8, 10))
            self.diary_text.insert("1.0", self.vm.diary_markdown)

    def _show_settings_view(self) -> None:
        self.collapse_button.config(text="←", command=self.show_dashboard)
        self._settings_repo_var = tk.StringVar(value=self.vm.settings.repository_path)
        self._settings_enabled_var = tk.BooleanVar(value=self.vm.settings.ai_enabled)
        self._settings_base_url_var = tk.StringVar(value=self.vm.settings.ai_base_url)
        self._settings_model_var = tk.StringVar(value=self.vm.settings.ai_model)
        self._settings_api_key_var = tk.StringVar(value=self.vm.settings.ai_api_key)

        panel = tk.Frame(
            self.content_frame,
            bg=COLORS["surface"],
            highlightthickness=1,
            highlightbackground=COLORS["line"],
        )
        panel.pack(fill="both", expand=True)
        tk.Label(
            panel,
            text="设置",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        ).pack(fill="x", padx=12, pady=(12, 2))
        tk.Label(
            panel,
            text="仓库和 AI 润色都在当前窗口内完成",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            anchor="w",
            font=("Segoe UI", 9),
        ).pack(fill="x", padx=12, pady=(0, 10))

        self._setting_entry(panel, "仓库路径", self._settings_repo_var, browse=True)
        self._setting_entry(panel, "AI 地址", self._settings_base_url_var)
        self._setting_entry(panel, "AI 模型", self._settings_model_var)
        self._setting_entry(panel, "API Key", self._settings_api_key_var, show="*")

        check = tk.Checkbutton(
            panel,
            text="启用 AI 增强",
            variable=self._settings_enabled_var,
            bg=COLORS["surface"],
            fg=COLORS["subtle"],
            selectcolor=COLORS["bg"],
            activebackground=COLORS["surface"],
            activeforeground=COLORS["text"],
            font=("Segoe UI", 9),
        )
        check.pack(anchor="w", padx=12, pady=(4, 8))

        actions = tk.Frame(panel, bg=COLORS["surface"])
        actions.pack(fill="x", padx=12, pady=(2, 12))
        self._button("保存设置", self._save_settings_from_panel, parent=actions, variant="primary").pack(
            side="right", padx=(6, 0)
        )
        self._button("返回", self.show_dashboard, parent=actions).pack(side="right")

    def _metric_card(self, parent: tk.Widget, label: str, value: str, accent: str) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=COLORS["surface_alt"],
            highlightthickness=1,
            highlightbackground=COLORS["line"],
        )
        tk.Label(
            card,
            text=label,
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            anchor="w",
            font=("Segoe UI", 8),
        ).pack(fill="x", padx=9, pady=(7, 0))
        tk.Label(
            card,
            text=value,
            bg=COLORS["surface_alt"],
            fg=accent,
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        ).pack(fill="x", padx=9, pady=(1, 7))
        return card

    def _setting_entry(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        show: str | None = None,
        browse: bool = False,
    ) -> None:
        row = tk.Frame(parent, bg=COLORS["surface"])
        row.pack(fill="x", padx=12, pady=5)
        tk.Label(
            row,
            text=label,
            bg=COLORS["surface"],
            fg=COLORS["subtle"],
            width=9,
            anchor="w",
            font=("Segoe UI", 9),
        ).pack(side="left")
        entry = tk.Entry(
            row,
            textvariable=variable,
            show=show,
            bg="#020617",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            bd=0,
            font=("Segoe UI", 9),
        )
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        if browse:
            self._button("浏览", lambda: self._browse_repository(variable), parent=row).pack(
                side="left", padx=(8, 0)
            )

    def _status_color(self) -> str:
        if "失败" in self.vm.status_text:
            return COLORS["danger"]
        if "生成" in self.vm.status_text or "刷新" in self.vm.status_text or "保存" in self.vm.status_text:
            return COLORS["accent"]
        if "选择" in self.vm.status_text:
            return COLORS["warning"]
        return COLORS["info"]

    def _bind_events(self) -> None:
        self.header.bind("<ButtonPress-1>", self._start_drag)
        self.header.bind("<B1-Motion>", self._drag)
        self.title_label.bind("<ButtonPress-1>", self._start_drag)
        self.title_label.bind("<B1-Motion>", self._drag)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

    def _restore_geometry(self) -> None:
        settings = self.vm.settings
        width = max(settings.window_width, 380)
        height = max(settings.window_height, 300)
        self.root.geometry(
            f"{width}x{height}+{settings.window_x}+{settings.window_y}"
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
        self.vm.status_text = "生成中..."
        self._refresh_labels()
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
        self._refresh_labels()
        self._resize_for_current_view()
        self._save_position()

    def select_repository(self) -> None:
        path = filedialog.askdirectory(title="选择 Git 仓库")
        if path:
            self.vm.show_dashboard()
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
        self.vm.show_settings()
        self._refresh_labels()
        self._resize_for_current_view()

    def _browse_repository(self, target: tk.StringVar) -> None:
        path = filedialog.askdirectory(title="选择 Git 仓库")
        if path:
            target.set(path)

    def show_dashboard(self) -> None:
        self.vm.show_dashboard()
        self._refresh_labels()
        self._resize_for_current_view()

    def _save_settings_from_panel(self) -> None:
        repo_path = self._settings_repo_var.get().strip()
        self.vm.update_settings(
            replace(
                self.vm.settings,
                repository_path=repo_path,
                ai_enabled=self._settings_enabled_var.get(),
                ai_base_url=self._settings_base_url_var.get().strip() or "https://api.openai.com/v1",
                ai_model=self._settings_model_var.get().strip() or "gpt-4.1-mini",
                ai_api_key=self._settings_api_key_var.get().strip(),
            )
        )
        self.vm.status_text = "设置已保存"
        self.vm.show_dashboard()
        self._refresh_labels()
        self._resize_for_current_view()
        if repo_path:
            self._run_background(lambda: self._refresh_repository(repo_path))

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
        self.root.after(0, self._show_generated_diary)

    def _show_generated_diary(self) -> None:
        self._refresh_labels()
        self._resize_for_current_view()

    def _refresh_labels(self) -> None:
        self.title_label.config(text=f"{self.vm.repository_name} · {self.vm.branch_name}")
        self._render_current_view()

    def _sync_detail_visibility(self, resize: bool) -> None:
        self._refresh_labels()
        if resize:
            self._resize_for_current_view()

    def _resize_for_current_view(self) -> None:
        if self.vm.current_view == "settings":
            width, height = 460, 440
        elif self.vm.is_expanded:
            width, height = 560, 600
        else:
            width, height = 380, 300
        self.root.geometry(f"{width}x{height}+{self.root.winfo_x()}+{self.root.winfo_y()}")

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
