"""GUI-friendly entry point for standalone packaged apps (.app / .exe / binary).

Defaults to Eco low-power mode and auto-detected OS language, and displays a
native dialog if camera permissions or startup errors occur (since double-clicked
apps have no visible terminal window).
"""

from __future__ import annotations

import sys
from typing import List, Optional

from blink_counter.cli import main as cli_main
from blink_counter.i18n import Translator


def _show_error_dialog(title: str, message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"{title}: {message}", file=sys.stderr)


def run_app(argv: Optional[List[str]] = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    # Strip macOS Finder `-psn_*` launch arguments if present
    cleaned = [a for a in raw_args if not a.startswith("-psn_")]

    # Default to battery-friendly Eco mode when launched via double-click with no args
    if not cleaned:
        cleaned = ["--eco"]

    tr = Translator("auto")
    try:
        return cli_main(cleaned)
    except Exception as exc:
        _show_error_dialog(tr.t("window_title"), str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(run_app())
