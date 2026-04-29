from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas
from ..db import get_db

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("", response_model=List[schemas.ScheduleOut])
def list_schedules(db: Session = Depends(get_db)):
    return crud.list_schedules(db)


@router.post("", response_model=schemas.ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(data: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    return crud.create_schedule(db, data)


@router.get("/{schedule_id}", response_model=schemas.ScheduleDetail)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    sched = crud.get_schedule(db, schedule_id)
    if not sched:
        raise HTTPException(404, "Schedule not found")
    return sched


@router.patch("/{schedule_id}", response_model=schemas.ScheduleOut)
def update_schedule(
    schedule_id: int,
    data: schemas.ScheduleUpdate,
    db: Session = Depends(get_db),
):
    sched = crud.get_schedule(db, schedule_id)
    if not sched:
        raise HTTPException(404, "Schedule not found")
    return crud.update_schedule(db, sched, data)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    sched = crud.get_schedule(db, schedule_id)
    if not sched:
        raise HTTPException(404, "Schedule not found")
    crud.delete_schedule(db, sched)
