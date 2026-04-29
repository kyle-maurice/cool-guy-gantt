"""Self-updating launcher for Cool Guy Gantt Chart Maker.

On launch:
  1. Checks GitHub for the latest commit on `main`.
  2. If newer than what's cached locally, downloads the source zip
     and extracts it to %LOCALAPPDATA%\\CoolGuyGantt\\app.
  3. Adds that folder to sys.path.
  4. Starts uvicorn in-process and opens the default browser.
  5. Stays running until Ctrl+C or the console window is closed.

Falls back to the last good cached copy if the network is unreachable.
"""
from __future__ import annotations

import io
import json
import os
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

REPO_OWNER = "kyle-maurice"
REPO_NAME = "cool-guy-gantt"
BRANCH = "main"

API_LATEST_COMMIT = (
    f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}"
)
ZIP_URL = (
    f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"
)

APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CoolGuyGantt"
SOURCE_DIR = APP_DIR / "source"           # current extracted source root
VERSION_FILE = APP_DIR / "version.json"   # {"sha": "<commit sha>"}
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
HTTP_TIMEOUT = 8  # seconds


# ------------------------------------------------------------------ logging
def log(msg: str) -> None:
    print(f"[launcher] {msg}", flush=True)


# ------------------------------------------------------------------ updater
def _read_local_sha() -> str | None:
    try:
        return json.loads(VERSION_FILE.read_text("utf-8")).get("sha")
    except Exception:
        return None


def _write_local_sha(sha: str) -> None:
    VERSION_FILE.write_text(json.dumps({"sha": sha}), encoding="utf-8")


def _fetch_remote_sha() -> str | None:
    try:
        req = urllib.request.Request(
            API_LATEST_COMMIT,
            headers={"User-Agent": "CoolGuyGantt-Launcher"},
        )
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))
            return data.get("sha")
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as e:
        log(f"Could not reach GitHub: {e}")
        return None


def _download_and_extract() -> bool:
    log(f"Downloading latest source from {ZIP_URL} ...")
    try:
        req = urllib.request.Request(
            ZIP_URL, headers={"User-Agent": "CoolGuyGantt-Launcher"}
        )
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT * 4) as r:
            buf = io.BytesIO(r.read())
    except Exception as e:
        log(f"Download failed: {e}")
        return False

    # Extract into a fresh temp dir, then atomically swap.
    tmp = APP_DIR / "_extract_tmp"
    if tmp.exists():
        _rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(buf) as zf:
            zf.extractall(tmp)
    except Exception as e:
        log(f"Extract failed: {e}")
        return False

    # GitHub zips contain a single top-level folder like "<repo>-<branch>".
    children = [p for p in tmp.iterdir() if p.is_dir()]
    if not children:
        log("Unexpected zip layout (no top-level folder).")
        return False
    extracted_root = children[0]

    if SOURCE_DIR.exists():
        _rmtree(SOURCE_DIR)
    extracted_root.rename(SOURCE_DIR)
    _rmtree(tmp)
    log(f"Source updated at {SOURCE_DIR}")
    return True


def _rmtree(path: Path) -> None:
    import shutil
    shutil.rmtree(path, ignore_errors=True)


def ensure_source() -> bool:
    """Make sure SOURCE_DIR holds an up-to-date copy. Returns True on success."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    remote = _fetch_remote_sha()
    local = _read_local_sha()

    have_source = SOURCE_DIR.exists() and (SOURCE_DIR / "app" / "main.py").exists()

    if remote and remote != local:
        log(f"Update available (remote={remote[:7]}, local={(local or 'none')[:7]}).")
        if _download_and_extract():
            _write_local_sha(remote)
            return True
        log("Falling back to cached copy.")
        return have_source

    if have_source:
        log(f"Using cached source ({(local or 'unknown')[:7]}).")
        return True

    if not have_source and remote is None:
        log("No cached source and GitHub unreachable.")
        return False

    # Edge: have remote but no local source (offline/no SHA mismatch path)
    if not have_source:
        if _download_and_extract() and remote:
            _write_local_sha(remote)
            return True
    return have_source


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
    # Run uvicorn from the source dir so SQLite / static paths resolve.
    os.chdir(source_dir)
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
        uvicorn.run(app, host=HOST, port=port, log_level="info")
    except KeyboardInterrupt:
        pass
    return 0


def main() -> int:
    print("Cool Guy Gantt Chart Maker")
    print("=" * 32)
    if not ensure_source():
        log(
            "ERROR: No source available. Connect to the internet and "
            "re-launch to download the latest version."
        )
        input("Press Enter to exit...")
        return 1
    return run_server(SOURCE_DIR)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
