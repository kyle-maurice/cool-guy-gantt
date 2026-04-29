from datetime import date, datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


Mode = Literal["day", "week"]


def _validate_half_step(value: float | None) -> float | None:
    if value is None:
        return value
    # Allow values that are multiples of 0.5 (covers integers too).
    doubled = round(value * 2)
    if abs(doubled / 2 - value) > 1e-9:
        raise ValueError("must be in increments of 0.5")
    return doubled / 2


# ---------- Dependency ----------
class DependencyBase(BaseModel):
    prerequisite_id: int


class DependencyCreate(DependencyBase):
    pass


class DependencyOut(BaseModel):
    id: int
    task_id: int
    prerequisite_id: int
    model_config = ConfigDict(from_attributes=True)


# ---------- Task ----------
class TaskBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    start_offset: float = Field(ge=0.0, default=0.0)
    duration: float = Field(gt=0.0, default=1.0)
    progress: float = Field(ge=0.0, le=1.0, default=0.0)
    color: Optional[str] = None

    @field_validator("start_offset", "duration", mode="after")
    @classmethod
    def _half_step(cls, v: float) -> float:
        return _validate_half_step(v)


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    start_offset: Optional[float] = Field(default=None, ge=0.0)
    duration: Optional[float] = Field(default=None, gt=0.0)
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    color: Optional[str] = None

    @field_validator("start_offset", "duration", mode="after")
    @classmethod
    def _half_step(cls, v: Optional[float]) -> Optional[float]:
        return _validate_half_step(v)


class TaskOut(TaskBase):
    id: int
    schedule_id: int
    dependencies: List[DependencyOut] = []
    model_config = ConfigDict(from_attributes=True)


# ---------- Schedule ----------
class ScheduleBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mode: Mode = "day"
    start_date: date = Field(default_factory=date.today)


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    mode: Optional[Mode] = None
    start_date: Optional[date] = None


class ScheduleOut(ScheduleBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ScheduleDetail(ScheduleOut):
    tasks: List[TaskOut] = []
