import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


def _resolve_db_path() -> str:
    """Return an absolute SQLite URL.

    Order of precedence:
      1. COOLGUYGANTT_DB env var (explicit override).
      2. %LOCALAPPDATA%\\CoolGuyGantt\\data\\gantt.db on Windows / ~/.coolguygantt/gantt.db elsewhere
         when running from the bundled launcher (detected via COOLGUYGANTT_DATA_DIR).
      3. ./gantt.db (legacy, used for local development).
    """
    override = os.environ.get("COOLGUYGANTT_DB")
    if override:
        return f"sqlite:///{override}"

    data_dir = os.environ.get("COOLGUYGANTT_DATA_DIR")
    if data_dir:
        p = Path(data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{(p / 'gantt.db').as_posix()}"

    return "sqlite:///./gantt.db"


SQLALCHEMY_DATABASE_URL = _resolve_db_path()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
