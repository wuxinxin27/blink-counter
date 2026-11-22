"""Module execution entry point (`python -m blink_counter`)."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
