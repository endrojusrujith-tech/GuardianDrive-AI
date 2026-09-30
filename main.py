"""
Guardian Drive AI - Main Root Launcher
Launches the full Windows desktop application by default.
"""
from __future__ import annotations

import sys
from app.main import run_app

if __name__ == "__main__":
    sys.exit(run_app())