from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas
from ..db import get_db

router = APIRouter(tags=["tasks"])


@router.get("/api/schedules/{schedule_id}/tasks", response_model=List[schemas.TaskOut])
def list_tasks(schedule_id: int, db: Session = Depends(get_db)):
    if not crud.get_schedule(db, schedule_id):
        raise HTTPException(404, "Schedule not found")
    return crud.list_tasks(db, schedule_id)


@router.post(
    "/api/schedules/{schedule_id}/tasks",
    response_model=schemas.TaskOut,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    schedule_id: int,
    data: schemas.TaskCreate,
    db: Session = Depends(get_db),
):
    if not crud.get_schedule(db, schedule_id):
        raise HTTPException(404, "Schedule not found")
    return crud.create_task(db, schedule_id, data)


@router.get("/api/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.patch("/api/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    data: schemas.TaskUpdate,
    db: Session = Depends(get_db),
):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return crud.update_task(db, task, data)


@router.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    crud.delete_task(db, task)
