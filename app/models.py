from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey, Float, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .db import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    mode = Column(String, nullable=False, default="day")  # 'day' | 'week'
    start_date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship(
        "Task", back_populates="schedule", cascade="all, delete-orphan"
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(
        Integer, ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String, nullable=False)
    start_offset = Column(Float, nullable=False, default=0.0)  # units from schedule start (0.5 step in week mode)
    duration = Column(Float, nullable=False, default=1.0)     # units (>= 0.5)
    progress = Column(Float, nullable=False, default=0.0)      # 0..1
    color = Column(String, nullable=True)                      # optional override

    schedule = relationship("Schedule", back_populates="tasks")

    dependencies = relationship(
        "Dependency",
        foreign_keys="Dependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
    )


class Dependency(Base):
    __tablename__ = "dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "prerequisite_id", name="uq_task_prereq"),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    prerequisite_id = Column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )

    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    prerequisite = relationship("Task", foreign_keys=[prerequisite_id])
