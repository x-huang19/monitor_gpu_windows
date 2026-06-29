from __future__ import annotations

import ctypes
import sys


def _hide_frozen_console() -> None:
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return

    console_window = ctypes.windll.kernel32.GetConsoleWindow()
    if console_window:
        ctypes.windll.user32.ShowWindow(console_window, 0)


_hide_frozen_console()

from app.main import run


if __name__ == "__main__":
    run()
