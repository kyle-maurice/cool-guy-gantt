from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..db import get_db

router = APIRouter(tags=["dependencies"])


@router.post(
    "/api/tasks/{task_id}/dependencies",
    response_model=schemas.DependencyOut,
    status_code=status.HTTP_201_CREATED,
)
def add_dependency(
    task_id: int,
    data: schemas.DependencyCreate,
    db: Session = Depends(get_db),
):
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    prereq = crud.get_task(db, data.prerequisite_id)
    if not prereq:
        raise HTTPException(404, "Prerequisite task not found")
    if prereq.schedule_id != task.schedule_id:
        raise HTTPException(400, "Prerequisite must belong to the same schedule")
    try:
        return crud.add_dependency(db, task, data.prerequisite_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete(
    "/api/dependencies/{dep_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_dependency(dep_id: int, db: Session = Depends(get_db)):
    dep = crud.get_dependency(db, dep_id)
    if not dep:
        raise HTTPException(404, "Dependency not found")
    crud.delete_dependency(db, dep)
