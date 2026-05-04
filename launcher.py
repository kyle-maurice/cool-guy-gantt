"""Standalone launcher for Cool Guy Gantt Chart Maker.

On launch:
  1. Resolves the local or bundled application source.
  2. Configures a persistent data directory under %LOCALAPPDATA%.
  3. Starts uvicorn in-process and opens the default browser.
  4. Stays running until Ctrl+C or the console window is closed.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CoolGuyGantt"
DATA_DIR = APP_DIR / "data"               # persistent user data (DB lives here)
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LAUNCHER_LOG = APP_DIR / "launcher.log"


# ------------------------------------------------------------------ logging
def log(msg: str) -> None:
    line = f"[launcher] {msg}"
    if sys.stdout is not None:
        print(line, flush=True)
        return
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with LAUNCHER_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def pause_if_interactive() -> None:
    if sys.stdin is None:
        return
    try:
        if sys.stdin.isatty():
            input("Press Enter to exit...")
    except Exception:
        pass


def resolve_source_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


# ------------------------------------------------------------------ server
def _pick_port(start: int) -> int:
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, port))
                return port
            except OSError:
                continue
    return start


def _open_browser_when_ready(url: str, port: int) -> None:
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                webbrowser.open(url)
                return
        except OSError:
            time.sleep(0.2)


def run_server(source_dir: Path) -> int:
    sys.path.insert(0, str(source_dir))
    # Run from the source dir so legacy relative paths continue to work.
    os.chdir(source_dir)

    # Tell the app where to keep its persistent data (DB lives outside source/).
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["COOLGUYGANTT_DATA_DIR"] = str(DATA_DIR)

    # One-time migration: if a legacy gantt.db exists inside source/, move it.
    legacy_db = source_dir / "gantt.db"
    target_db = DATA_DIR / "gantt.db"
    if legacy_db.exists() and not target_db.exists():
        try:
            target_db.write_bytes(legacy_db.read_bytes())
            legacy_db.unlink(missing_ok=True)
            log(f"Migrated existing gantt.db to {target_db}")
        except OSError as e:
            log(f"DB migration warning: {e}")

    log(f"Database: {target_db}")

    try:
        import uvicorn  # bundled by PyInstaller
        from app.main import app  # type: ignore
    except Exception as e:
        log(f"Failed to import app: {e}")
        traceback.print_exc()
        return 2

    port = _pick_port(DEFAULT_PORT)
    url = f"http://{HOST}:{port}"
    log(f"Starting server on {url}")
    threading.Thread(
        target=_open_browser_when_ready, args=(url, port), daemon=True
    ).start()

    try:
        # In windowed mode, stdin/stderr may be None; avoid uvicorn's default
        # logging config because it expects terminal streams.
        uvicorn.run(
            app,
            host=HOST,
            port=port,
            log_level="info",
            log_config=None,
            access_log=False,
        )
    except KeyboardInterrupt:
        pass
    return 0


def main() -> int:
    log("Cool Guy Gantt Chart Maker")
    log("=" * 32)
    source_dir = resolve_source_dir()
    if not (source_dir / "app" / "main.py").exists():
        log(f"ERROR: App source not found in {source_dir}")
        pause_if_interactive()
        return 1
    return run_server(source_dir)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log("Unhandled launcher error:")
        log(traceback.format_exc())
        pause_if_interactive()
        sys.exit(1)
