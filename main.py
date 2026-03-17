"""Точка входа CLI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.presentation.cli.app import app  # noqa: E402

if __name__ == "__main__":
    app()