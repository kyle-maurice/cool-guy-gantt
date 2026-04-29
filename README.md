# Gantt Chart

A browser-based Gantt chart application built with FastAPI + D3.js, styled with the Lam Research color palette.

## Features

- Multiple named schedules
- Tasks with names, start offset, duration, and progress
- Prerequisites with cycle detection
- Day or week-based scheduling per schedule
- Drag to move tasks; drag the right edge to resize duration
- Click any task bar to edit
- SQLite persistence (single file, no setup required)

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Tests

```powershell
pytest -q
```

## Project Layout

```
app/        FastAPI app, models, routers, CRUD
static/     CSS theme + D3 Gantt rendering
templates/  Jinja2 HTML
tests/      pytest suite
```

## Notes

- Each schedule stores its own mode (`day` or `week`). Task durations are stored as integer units of that mode.
- Switching a schedule's mode keeps unit values; the visual axis adjusts automatically.
- Dependencies are validated server-side to prevent cycles and cross-schedule references.
