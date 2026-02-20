"""
Tasks API Router
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import asyncio

from app.models import Task, TaskLog, get_db
from app.models.schemas import (
    TaskCreate, TaskUpdate, TaskResponse, TaskLogResponse,
    DashboardStats, CronValidateRequest, CronValidateResponse
)
from app.services.scheduler import TaskSchedulerService
from app.services.executor import TaskExecutor

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Global scheduler service (initialized in main.py)
scheduler_service: TaskSchedulerService = None

def set_scheduler_service(service: TaskSchedulerService):
    global scheduler_service
    scheduler_service = service

@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task"""
    db_task = Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Add to scheduler
    await scheduler_service.add_task(db_task)
    
    return db_task

@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all tasks"""
    query = db.query(Task)
    if active_only:
        query = query.filter(Task.is_enabled == True)
    return query.offset(skip).limit(limit).all()

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get a specific task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    """Update a task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Update fields
    for field, value in task_update.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    
    # Update scheduler
    await scheduler_service.update_task(task)
    
    return task

@router.delete("/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Remove from scheduler
    await scheduler_service.remove_task(task_id)
    
    # Delete logs
    db.query(TaskLog).filter(TaskLog.task_id == task_id).delete()
    
    # Delete task
    db.delete(task)
    db.commit()
    
    return {"message": "Task deleted successfully"}

@router.post("/{task_id}/run")
async def run_task_now(task_id: int, db: Session = Depends(get_db)):
    """Manually trigger a task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        log = await scheduler_service.run_task_now(task_id, trigger_type="manual")
        return {"message": "Task executed", "log_id": log.id if log else None}
