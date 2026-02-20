"""
Task Scheduler - Main Application
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os

from app.models import init_db, get_db as get_db_session
from app.routers import tasks
from app.services.scheduler import TaskSchedulerService

# Initialize database
SessionLocal = init_db("./data/scheduler.db")

# Create scheduler service
db_session = SessionLocal()
scheduler_service = TaskSchedulerService(db_session)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler_service.start()
    tasks.set_scheduler_service(scheduler_service)
    
    # Load existing tasks
    from app.models import Task
    db = SessionLocal()
    all_tasks = db.query(Task).all()
    for task in all_tasks:
        await scheduler_service.add_task(task)
    db.close()
    
    yield
    
    # Shutdown
    scheduler_service.shutdown()
    db_session.close()

app = FastAPI(
    title="Task Scheduler",
    description="A modern task scheduling and automation platform",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(tasks.router)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    """Tasks management page"""
    return templates.TemplateResponse("tasks.html", {"request": request})

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Logs viewer page"""
    return templates.TemplateResponse("logs.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scheduler_running": scheduler_service.scheduler.running,
        "scheduled_jobs": len(scheduler_service.get_scheduler_jobs())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
