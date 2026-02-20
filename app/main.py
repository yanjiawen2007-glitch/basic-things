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
from app.routers import ai as ai_router
from app.services.scheduler import TaskSchedulerService
from app.services.ai_service import AIService

# Initialize database
SessionLocal = init_db("./data/scheduler.db")

# Create services
db_session = SessionLocal()
scheduler_service = TaskSchedulerService(db_session)
# Auto-select best available model
ai_service = AIService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler_service.start()
    tasks.set_scheduler_service(scheduler_service)
    ai_router.set_ai_service(ai_service)
    
    # Print selected model info
    status = ai_service.get_status()
    if status["available"]:
        print(f"✅ AI 服务已启动，使用模型: {status['model']}")
        print(f"📋 可用模型: {', '.join(status['available_models'])}")
    else:
        print("⚠️  AI 服务未启动，将使用规则模式")
    
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
    description="A modern task scheduling and automation platform with AI",
    version="1.1.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(tasks.router)
app.include_router(ai_router.router)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/index", response_class=HTMLResponse)
async def index_page(request: Request):
    """Navigation index page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    """Tasks management page"""
    return templates.TemplateResponse("tasks.html", {"request": request})

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Logs viewer page"""
    return templates.TemplateResponse("logs.html", {"request": request})

@app.get("/ai", response_class=HTMLResponse)
async def ai_page(request: Request):
    """AI assistant page"""
    return templates.TemplateResponse("ai.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scheduler_running": scheduler_service.scheduler.running,
        "scheduled_jobs": len(scheduler_service.get_scheduler_jobs()),
        "ai_available": ai_service.get_status()["available"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
