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

@router.post("", response_model=TaskResponse)
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task"""
    db_task = Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Add to scheduler
    await scheduler_service.add_task(db_task)
    
    return db_task

@router.get("", response_model=List[TaskResponse])
def list_tasks(
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all tasks"""
    query = db.query(Task)
    if active_only:
        query = query.filter(Task.is_active == True)
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{task_id}/toggle")
async def toggle_task(task_id: int, db: Session = Depends(get_db)):
    """Enable/disable a task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_active = not task.is_active
    db.commit()
    
    # Update scheduler
    await scheduler_service.update_task(task)
    
    return {"message": f"Task {'enabled' if task.is_active else 'disabled'}", "is_active": task.is_active}

@router.get("/{task_id}/logs", response_model=List[TaskLogResponse])
def get_task_logs(
    task_id: int, 
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get execution logs for a task"""
    logs = db.query(TaskLog).filter(
        TaskLog.task_id == task_id
    ).order_by(TaskLog.started_at.desc()).limit(limit).all()
    return logs

@router.get("/logs/recent", response_model=List[TaskLogResponse])
def get_recent_logs(limit: int = 20, db: Session = Depends(get_db)):
    """Get recent execution logs across all tasks"""
    logs = db.query(TaskLog).order_by(
        TaskLog.started_at.desc()
    ).limit(limit).all()
    return logs

@router.post("/validate-cron", response_model=CronValidateResponse)
async def validate_cron(request: CronValidateRequest):
    """Validate a cron expression and show next run times"""
    try:
        from croniter import croniter
        from datetime import datetime
        
        cron = croniter(request.expression, datetime.utcnow())
        next_runs = [cron.get_next(datetime).isoformat() for _ in range(5)]
        
        return CronValidateResponse(valid=True, next_runs=next_runs)
    except Exception as e:
        return CronValidateResponse(valid=False, next_runs=[], error=str(e))

@router.get("/stats/dashboard", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    total_tasks = db.query(Task).count()
    active_tasks = db.query(Task).filter(Task.is_active == True).count()
    running_tasks = db.query(Task).filter(Task.is_running == True).count()
    
    total_runs = db.query(TaskLog).count()
    success_runs = db.query(TaskLog).filter(TaskLog.status == "success").count()
    
    success_rate = (success_runs / total_runs * 100) if total_runs > 0 else 0
    
    recent_logs = db.query(TaskLog).order_by(
        TaskLog.started_at.desc()
    ).limit(10).all()
    
    upcoming_tasks = db.query(Task).filter(
        Task.is_active == True,
        Task.next_run_at != None
    ).order_by(Task.next_run_at).limit(5).all()
    
    return DashboardStats(
        total_tasks=total_tasks,
        active_tasks=active_tasks,
        running_tasks=running_tasks,
        total_runs=total_runs,
        success_rate=round(success_rate, 2),
        recent_logs=recent_logs,
        upcoming_tasks=upcoming_tasks
    )
