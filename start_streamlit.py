"""Spolehlivý spouštěč Streamlit aplikace nezávislý na pracovním adresáři.

V PyCharmu lze tento soubor spustit běžným tlačítkem Run. Použije se
aktuálně zvolený Python interpreter a absolutní cesta k webové aplikaci.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent
    app_path = project_root / "extra_renta" / "web_app" / "app.py"

    if not app_path.is_file():
        print(f"Chyba: spouštěcí soubor nebyl nalezen: {app_path}", file=sys.stderr)
        return 2

    command = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    print(f"Spouštím Extra Renta: {app_path}")
    try:
        return subprocess.call(command, cwd=project_root)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
