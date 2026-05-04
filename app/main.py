from pathlib import Path
import os
import threading
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response

from .db import Base, engine
from . import models  # noqa: F401  (register models)
from .routers import schedules, tasks, dependencies

BASE_DIR = Path(__file__).resolve().parent.parent

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cool Guy Gantt Chart Maker")


AUTO_EXIT_ON_IDLE = os.environ.get("COOLGUYGANTT_AUTO_EXIT_ON_IDLE") == "1"
SESSION_STALE_SECONDS = float(os.environ.get("COOLGUYGANTT_SESSION_STALE_SECONDS", "40"))
EMPTY_EXIT_GRACE_SECONDS = float(os.environ.get("COOLGUYGANTT_EMPTY_EXIT_GRACE_SECONDS", "8"))
WATCHDOG_SLEEP_SECONDS = float(os.environ.get("COOLGUYGANTT_WATCHDOG_SLEEP_SECONDS", "2"))

_sessions_lock = threading.Lock()
_sessions: dict[str, float] = {}
_had_any_session = False
_empty_since: float | None = None


def _cleanup_stale_sessions(now: float) -> None:
    stale = [sid for sid, ts in _sessions.items() if now - ts > SESSION_STALE_SECONDS]
    for sid in stale:
        _sessions.pop(sid, None)


def _watch_for_all_tabs_closed() -> None:
    """When launched via EXE, stop the process once all browser tabs are gone."""
    global _empty_since
    while True:
        time.sleep(max(0.5, WATCHDOG_SLEEP_SECONDS))
        now = time.monotonic()
        with _sessions_lock:
            _cleanup_stale_sessions(now)
            has_sessions = bool(_sessions)
            if has_sessions:
                _empty_since = None
                continue
            if not _had_any_session:
                continue
            if _empty_since is None:
                _empty_since = now
                continue
            if now - _empty_since < EMPTY_EXIT_GRACE_SECONDS:
                continue
        os._exit(0)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(schedules.router)
app.include_router(tasks.router)
app.include_router(dependencies.router)


if AUTO_EXIT_ON_IDLE:
    threading.Thread(target=_watch_for_all_tabs_closed, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/session/heartbeat", status_code=204)
def session_heartbeat(sid: str):
    global _had_any_session
    with _sessions_lock:
        _sessions[sid] = time.monotonic()
        _had_any_session = True
    return Response(status_code=204)


@app.post("/api/session/close", status_code=204)
def session_close(sid: str):
    with _sessions_lock:
        _sessions.pop(sid, None)
    return Response(status_code=204)
