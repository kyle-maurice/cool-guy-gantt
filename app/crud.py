from typing import Dict, List, Set
from sqlalchemy.orm import Session
from . import models, schemas


# ---------- Schedules ----------
def list_schedules(db: Session) -> List[models.Schedule]:
    return db.query(models.Schedule).order_by(models.Schedule.created_at.desc()).all()


def get_schedule(db: Session, schedule_id: int) -> models.Schedule | None:
    return db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()


def create_schedule(db: Session, data: schemas.ScheduleCreate) -> models.Schedule:
    sched = models.Schedule(**data.model_dump())
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


def update_schedule(
    db: Session, sched: models.Schedule, data: schemas.ScheduleUpdate
) -> models.Schedule:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(sched, k, v)
    db.commit()
    db.refresh(sched)
    return sched


def delete_schedule(db: Session, sched: models.Schedule) -> None:
    db.delete(sched)
    db.commit()


# ---------- Tasks ----------
def get_task(db: Session, task_id: int) -> models.Task | None:
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def list_tasks(db: Session, schedule_id: int) -> List[models.Task]:
    return (
        db.query(models.Task)
        .filter(models.Task.schedule_id == schedule_id)
        .order_by(models.Task.start_offset, models.Task.id)
        .all()
    )


def create_task(
    db: Session, schedule_id: int, data: schemas.TaskCreate
) -> models.Task:
    task = models.Task(schedule_id=schedule_id, **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(
    db: Session, task: models.Task, data: schemas.TaskUpdate
) -> models.Task:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: models.Task) -> None:
    db.delete(task)
    db.commit()


# ---------- Dependencies ----------
def _build_adjacency(db: Session, schedule_id: int) -> Dict[int, Set[int]]:
    """Map task_id -> set of prerequisite task ids for the schedule."""
    adj: Dict[int, Set[int]] = {}
    rows = (
        db.query(models.Dependency)
        .join(models.Task, models.Task.id == models.Dependency.task_id)
        .filter(models.Task.schedule_id == schedule_id)
        .all()
    )
    for r in rows:
        adj.setdefault(r.task_id, set()).add(r.prerequisite_id)
    return adj


def would_create_cycle(
    adj: Dict[int, Set[int]], task_id: int, prereq_id: int
) -> bool:
    """Adding edge task_id -> prereq_id (task depends on prereq).
    Cycle exists if prereq (transitively) already depends on task_id.
    """
    if task_id == prereq_id:
        return True
    stack = [prereq_id]
    seen: Set[int] = set()
    while stack:
        node = stack.pop()
        if node == task_id:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adj.get(node, ()))
    return False


def add_dependency(
    db: Session, task: models.Task, prereq_id: int
) -> models.Dependency:
    adj = _build_adjacency(db, task.schedule_id)
    # include the new edge for cycle check
    if would_create_cycle(adj, task.id, prereq_id):
        raise ValueError("Adding this dependency would create a cycle.")
    dep = models.Dependency(task_id=task.id, prerequisite_id=prereq_id)
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep


def get_dependency(db: Session, dep_id: int) -> models.Dependency | None:
    return (
        db.query(models.Dependency).filter(models.Dependency.id == dep_id).first()
    )


def delete_dependency(db: Session, dep: models.Dependency) -> None:
    db.delete(dep)
    db.commit()
