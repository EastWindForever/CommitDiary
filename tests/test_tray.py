import ctypes
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from commitdiary.tray import configure_window_proc_api


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


if __name__ == "__main__":
    unittest.main()
