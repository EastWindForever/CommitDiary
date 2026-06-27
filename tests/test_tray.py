import ctypes
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.tray import WindowsTrayIcon, configure_window_proc_api


class FakeWinApiFunction:
    def __init__(self):
        self.argtypes = None
        self.restype = None


class FakeUser32:
    def __init__(self):
        self.CallWindowProcW = FakeWinApiFunction()
        self.SetWindowLongPtrW = FakeWinApiFunction()


class TrayWinApiTests(unittest.TestCase):
    def test_configure_window_proc_api_uses_pointer_sized_call_window_proc(self):
        user32 = FakeUser32()

        configure_window_proc_api(user32)

        self.assertEqual(ctypes.c_void_p, user32.CallWindowProcW.argtypes[0])
        self.assertEqual(ctypes.c_void_p, user32.SetWindowLongPtrW.restype)

    def test_dispose_deletes_tray_icon_once(self):
        tray = WindowsTrayIcon.__new__(WindowsTrayIcon)
        tray._shell32 = FakeShell32()
        tray._icon_data = WindowsTrayIcon.NOTIFYICONDATAW()
        tray._old_wndproc = 123
        tray._hwnd = 456
        tray._set_wndproc = lambda hwnd, proc: None
        tray._disposed = False

        tray.dispose()
        tray.dispose()

        self.assertEqual([(WindowsTrayIcon.NIM_DELETE, tray._icon_data)], tray._shell32.calls)


class FakeShell32:
    def __init__(self):
        self.calls = []

    def Shell_NotifyIconW(self, action, data):
        self.calls.append((action, data._obj))
        return True


if __name__ == "__main__":
    unittest.main()
