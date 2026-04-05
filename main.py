"""
GitHub Repository Analyzer — application entry point.
Run from this directory: python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on path when run as script
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    from data.database_manager import DatabaseManager
    from ui.app import App

    exports_dir = _ROOT / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    database_dir = _ROOT / "database"
    database_dir.mkdir(parents=True, exist_ok=True)

    # Default DB: database/app.db; optional DATABASE_PATH env override (see README).
    db = DatabaseManager()
    db.initialize()

    app = App(db_manager=db)
    app.mainloop()


if __name__ == "__main__":
    main()
