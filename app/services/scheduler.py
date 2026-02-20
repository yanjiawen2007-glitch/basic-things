"""
Task Scheduler Service - Manages APScheduler and task lifecycle
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from typing import Optional, List
import asyncio
from loguru import logger

from app.models import Task, TaskLog
from app.models.schemas import TaskType
from app.services.executor import TaskExecutor

class TaskSchedulerService:
    def __init__(self, db_session):
        self.db = db_session
        self.scheduler = AsyncIOScheduler()
        self.executor = TaskExecutor()
        self._running_tasks = set()
        
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Task scheduler started")
        
    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Task scheduler shutdown")
        
    async def add_task(self, task: Task) -> bool:
        """Add a task to the scheduler"""
        try:
            job_id = f"task_{task.id}"
            
            # Remove existing job if present
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            if not task.is_active:
                return True
            
            # Parse cron expression
            cron_parts = task.cron_expression.split()
            if len(cron_parts) != 5:
                logger.error(f"Invalid cron expression for task {task.id}: {task.cron_expression}")
                return False
            
            trigger = CronTrigger(
                minute=cron_parts[0],
                hour=cron_parts[1],
                day=cron_parts[2],
                month=cron_parts[3],
                day_of_week=cron_parts[4]
            )
            
            # Add job to scheduler
            self.scheduler.add_job(
                func=self._run_task,
                trigger=trigger,
                id=job_id,
                args=[task.id],
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            # Update next run time
            job = self.scheduler.get_job(job_id)
            if job:
                task.next_run_at = job.next_run_time
                self.db.commit()
            
            logger.info(f"Task {task.id} ({task.name}) scheduled with cron: {task.cron_expression}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule task {task.id}: {e}")
            return False
    
    async def remove_task(self, task_id: int):
        """Remove a task from the scheduler"""
        job_id = f"task_{task_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Task {task_id} removed from scheduler")
    
    async def update_task(self, task: Task) -> bool:
        """Update a scheduled task"""
        await self.remove_task(task.id)
        return await self.add_task(task)
    
    async def _run_task(self, task_id: int):
        """Execute a task (called by scheduler)"""
        if task_id in self._running_tasks:
            logger.warning(f"Task {task_id} is already running, skipping")
            return
        
        self._running_tasks.add(task_id)
        task = None
        
        try:
            # Get task from database
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task or not task.is_active:
                return
            
            # Update task status
            task.is_running = True
            task.last_run_at = datetime.utcnow()
            task.run_count += 1
            self.db.commit()
            
            # Create log entry
            log = TaskLog(
                task_id=task.id,
                task_name=task.name,
                status="running",
                trigger_type="scheduled"
            )
            self.db.add(log)
            self.db.commit()
            
            # Execute task
            result = await self.executor.execute(
                task.id,
                task.name,
                TaskType(task.task_type),
                task.config
            )
            
            # Update log
            log.status = result["status"]
            log.completed_at = result["completed_at"]
            log.duration_ms = result["duration_ms"]
            log.output = result["output"]
            log.error_message = result["error_message"]
            log.exit_code = result["exit_code"]
            
            # Update task stats
            if result["status"] == "success":
                task.success_count += 1
            else:
                task.failure_count += 1
            
            task.is_running = False
            
            # Update next run time
            job = self.scheduler.get_job(f"task_{task.id}")
            if job:
                task.next_run_at = job.next_run_time
            
            self.db.commit()
            
            # Send notification if configured
            if (result["status"] == "failed" and task.notify_on_failure) or \
               (result["status"] == "success" and task.notify_on_success):
                await self._send_notification(task, result)
            
            logger.info(f"Task {task_id} completed with status: {result['status']}")
            
        except Exception as e:
            logger.error(f"Error running task {task_id}: {e}")
            if task:
                task.is_running = False
                self.db.commit()
        finally:
            self._running_tasks.discard(task_id)
    
    async def run_task_now(self, task_id: int, trigger_type: str = "manual") -> Optional[TaskLog]:
        """Manually trigger a task execution"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        if task_id in self._running_tasks:
            raise ValueError("Task is already running")
        
        self._running_tasks.add(task_id)
        
        try:
            task.is_running = True
            task.last_run_at = datetime.utcnow()
            task.run_count += 1
            self.db.commit()
            
            log = TaskLog(
                task_id=task.id,
                task_name=task.name,
                status="running",
                trigger_type=trigger_type
            )
            self.db.add(log)
            self.db.commit()
            
            result = await self.executor.execute(
                task.id,
                task.name,
                TaskType(task.task_type),
                task.config
            )
            
            log.status = result["status"]
            log.completed_at = result["completed_at"]
            log.duration_ms = result["duration_ms"]
            log.output = result["output"]
            log.error_message = result["error_message"]
            log.exit_code = result["exit_code"]
            
            if result["status"] == "success":
                task.success_count += 1
            else:
                task.failure_count += 1
            
            task.is_running = False
            self.db.commit()
            
            return log
            
        finally:
            self._running_tasks.discard(task_id)
    
    async def _send_notification(self, task: Task, result: dict):
        """Send notification (placeholder implementation)"""
        # TODO: Implement email/webhook notification
        logger.info(f"Would send notification for task {task.id} to {task.notification_email}")
    
    def get_scheduler_jobs(self) -> List[dict]:
        """Get all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger)
            })
        return jobs
