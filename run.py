from __future__ import annotations

import ctypes
import os
import sys


def _ensure_standard_streams() -> None:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _hide_frozen_console() -> None:
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return

    console_window = ctypes.windll.kernel32.GetConsoleWindow()
    if console_window:
        ctypes.windll.user32.ShowWindow(console_window, 0)


_ensure_standard_streams()
_hide_frozen_console()

from app.main import run


if __name__ == "__main__":
    run()
