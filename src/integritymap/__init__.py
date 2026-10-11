import os
import sys
from pathlib import Path


def main() -> None:
    """Start the explorer: `uv run integritymap`."""
    from streamlit.web import cli

    os.chdir(Path(__file__).resolve().parents[2])  # .streamlit/config.toml holds the theme
    sys.argv = ["streamlit", "run", str(Path(__file__).with_name("app.py")), *sys.argv[1:]]
    cli.main()
