from datetime import date, datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field, ConfigDict


Mode = Literal["day", "week"]


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
    start_offset: int = Field(ge=0, default=0)
    duration: int = Field(ge=1, default=1)
    progress: float = Field(ge=0.0, le=1.0, default=0.0)
    color: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    start_offset: Optional[int] = Field(default=None, ge=0)
    duration: Optional[int] = Field(default=None, ge=1)
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    color: Optional[str] = None


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
