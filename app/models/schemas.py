"""
Pydantic schemas for API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class TaskType(str, Enum):
    HTTP = "http"
    SHELL = "shell"
    PYTHON = "python"
    BACKUP = "backup"

class TaskStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"

class HTTPConfig(BaseModel):
    url: str = Field(..., description="Target URL")
    method: str = Field(default="GET", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Request headers")
    body: Optional[str] = Field(default=None, description="Request body")
    timeout: int = Field(default=30, description="Timeout in seconds")

class ShellConfig(BaseModel):
    command: str = Field(..., description="Shell command to execute")
    working_dir: Optional[str] = Field(default=None, description="Working directory")
    timeout: int = Field(default=300, description="Timeout in seconds")
    env_vars: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")

class PythonConfig(BaseModel):
    code: str = Field(..., description="Python code to execute")
    requirements: Optional[List[str]] = Field(default=None, description="Additional pip packages")
    timeout: int = Field(default=300, description="Timeout in seconds")

class BackupConfig(BaseModel):
    source_path: str = Field(..., description="Source directory or file")
    destination_path: str = Field(..., description="Backup destination")
    compress: bool = Field(default=True, description="Compress backup")
    retention_days: int = Field(default=7, description="Keep backups for N days")

class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    task_type: TaskType
    cron_expression: str = Field(..., description="Cron expression (e.g., '0 9 * * *')")
    config: Dict[str, Any]
    is_active: bool = Field(default=True)
    notify_on_success: bool = Field(default=False)
    notify_on_failure: bool = Field(default=True)
    notification_email: Optional[str] = Field(default=None)

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    cron_expression: Optional[str] = Field(default=None)
    config: Optional[Dict[str, Any]] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    notify_on_success: Optional[bool] = Field(default=None)
    notify_on_failure: Optional[bool] = Field(default=None)
    notification_email: Optional[str] = Field(default=None)

class TaskResponse(TaskBase):
    id: int
    is_running: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    run_count: int
    success_count: int
    failure_count: int
    
    class Config:
        from_attributes = True

class TaskLogBase(BaseModel):
    task_id: int
    task_name: str
    status: str
    trigger_type: str = "scheduled"

class TaskLogResponse(TaskLogBase):
    id: int
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    output: Optional[str]
    error_message: Optional[str]
    exit_code: Optional[int]
    
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_tasks: int
    active_tasks: int
    running_tasks: int
    total_runs: int
    success_rate: float
    recent_logs: List[TaskLogResponse]
    upcoming_tasks: List[TaskResponse]

class CronValidateRequest(BaseModel):
    expression: str

class CronValidateResponse(BaseModel):
    valid: bool
    next_runs: List[str]
    error: Optional[str] = None
