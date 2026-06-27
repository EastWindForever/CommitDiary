from __future__ import annotations

import ctypes
import tkinter as tk
from ctypes import wintypes
from typing import Callable


class WindowsTrayIcon:
    WM_USER = 0x0400
    WM_LBUTTONUP = 0x0202
    WM_RBUTTONUP = 0x0205
    NIM_ADD = 0x00000000
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    GWL_WNDPROC = -4
    IDI_APPLICATION = 32512

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", wintypes.HICON),
            ("szTip", wintypes.WCHAR * 128),
        ]

    def __init__(
        self,
        root: tk.Tk,
        on_show: Callable[[], None],
        on_hide: Callable[[], None],
        on_select_repository: Callable[[], None],
        on_settings: Callable[[], None],
        on_exit: Callable[[], None],
    ):
        self._root = root
        self._on_show = on_show
        self._on_hide = on_hide
        self._callback_message = self.WM_USER + 25
        self._user32 = ctypes.windll.user32
        self._shell32 = ctypes.windll.shell32
        self._hwnd = root.winfo_id()
        self._menu = tk.Menu(root, tearoff=0)
        self._menu.add_command(label="显示窗口", command=on_show)
        self._menu.add_command(label="隐藏窗口", command=on_hide)
        self._menu.add_command(label="选择仓库", command=on_select_repository)
        self._menu.add_command(label="设置", command=on_settings)
        self._menu.add_separator()
        self._menu.add_command(label="退出", command=on_exit)
        self._wndproc_type = ctypes.WINFUNCTYPE(
            wintypes.LPARAM,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )
        self._new_wndproc = self._wndproc_type(self._wndproc)
        self._old_wndproc = self._set_wndproc(self._hwnd, self._new_wndproc)
        self._icon_data = self._make_icon_data()
        self._shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(self._icon_data))

    def dispose(self) -> None:
        self._shell32.Shell_NotifyIconW(self.NIM_DELETE, ctypes.byref(self._icon_data))
        if self._old_wndproc:
            self._set_wndproc(self._hwnd, self._old_wndproc)

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == self._callback_message:
            if lparam == self.WM_LBUTTONUP:
                self._root.after(0, self._on_show)
            elif lparam == self.WM_RBUTTONUP:
                self._root.after(0, self._show_menu)
            return 0
        return self._user32.CallWindowProcW(self._old_wndproc, hwnd, msg, wparam, lparam)

    def _show_menu(self) -> None:
        point = wintypes.POINT()
        self._user32.GetCursorPos(ctypes.byref(point))
        self._menu.tk_popup(point.x, point.y)

    def _make_icon_data(self):
        icon = self._user32.LoadIconW(None, self.IDI_APPLICATION)
        data = self.NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(self.NOTIFYICONDATAW)
        data.hWnd = self._hwnd
        data.uID = 1
        data.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
        data.uCallbackMessage = self._callback_message
        data.hIcon = icon
        data.szTip = "CommitDiary"
        return data

    def _set_wndproc(self, hwnd, proc):
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            set_window_long = self._user32.SetWindowLongPtrW
        else:
            set_window_long = self._user32.SetWindowLongW
        set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        set_window_long.restype = ctypes.c_void_p
        return set_window_long(hwnd, self.GWL_WNDPROC, proc)
