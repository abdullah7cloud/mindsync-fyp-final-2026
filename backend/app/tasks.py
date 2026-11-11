"""
Task CRUD routes. Every route is scoped to the authenticated user
(owner_id == current_user.id) so one user can never read, edit or delete
another user's tasks — this is enforced in the query itself, not just by
hiding the option in the UI.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Task, User
from app.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


# Data flow for every route below:
#   browser (React, sends JWT) -> get_current_user decodes it -> the query is filtered by owner_id ->
#   PostgreSQL row <-> Task (SQLAlchemy model) <-> TaskOut (Pydantic schema, what the browser receives).
# Pydantic validates the INPUT (TaskCreate/TaskUpdate), the database CHECK constraints validate it AGAIN.


async def _get_owned_task(task_id: uuid.UUID, current_user: User, db: AsyncSession) -> Task:
    task = await db.get(Task, task_id)
    if task is None or task.owner_id != current_user.id:
        # 404, not 403: do not reveal that a task with this id exists
        # for a different user.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Task]:
    # The WHERE owner_id clause is the access control: a user only ever sees their own rows.
    result = await db.scalars(
        select(Task).where(Task.owner_id == current_user.id).order_by(Task.deadline.asc())
    )
    return list(result.all())


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Task:
    # owner_id comes from the verified token, never from the request body, so a client cannot
    # create a task for someone else (mass-assignment defence).
    task = Task(owner_id=current_user.id, **payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Task:
    return await _get_owned_task(task_id, current_user, db)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Task:
    task = await _get_owned_task(task_id, current_user, db)
    # exclude_unset: only change the fields the client actually sent (PATCH semantics).
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(task, field, value)
    # Record WHEN it was finished (drives the progress charts); clear it if the task is re-opened.
    if changes.get("status") == "completed" and task.completed_at is None:
        task.completed_at = datetime.now(timezone.utc)
    elif changes.get("status") == "pending":
        task.completed_at = None
    if "deadline" in changes or changes.get("status") == "pending":
        task.reminder_sent_at = None   # new deadline -> the 2-day email can be sent again
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    task = await _get_owned_task(task_id, current_user, db)
    await db.delete(task)
    await db.commit()
