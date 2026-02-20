""" Task Scheduler - Main Application """

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os

from app.models import init_db
try:
    init_db()
    print("Database initialized successfully")
except Exception as e:
    print(f"Database initialization failed: {e}")
    raise

from app.models import SessionLocal, get_db as get_db_session
print(f"SessionLocal imported: {SessionLocal}")

from app.routers import tasks_router, ai_router, messages_router
from app.services.scheduler import TaskSchedulerService
from app.services.ai_service import AIService

db_session = SessionLocal()
scheduler_service = TaskSchedulerService(db_session)
ai_service = AIService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_service.start()
    tasks_router.set_scheduler_service(scheduler_service)
    ai_router.set_ai_service(ai_service)

    status = ai_service.get_status()
    if status["available"]:
        print(f"AI service started, model: {status['model']}")
        print(f"Available models: {', '.join(status['available_models'])}")
    else:
        print("AI service not started, using rule mode")

    from app.models import Task
    db = SessionLocal()
    all_tasks = db.query(Task).all()
    for task in all_tasks:
        await scheduler_service.add_task(task)
    db.close()

    yield

    scheduler_service.shutdown()
    db_session.close()


app = FastAPI(
    title="Task Scheduler",
    description="A modern task scheduling and automation platform with AI",
    version="1.1.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(tasks_router)
app.include_router(ai_router)
app.include_router(messages_router)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/index", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    return templates.TemplateResponse("tasks.html", {"request": request})


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    return templates.TemplateResponse("logs.html", {"request": request})


@app.get("/ai", response_class=HTMLResponse)
async def ai_page(request: Request):
    return templates.TemplateResponse("ai.html", {"request": request})


@app.get("/messages", response_class=HTMLResponse)
async def messages_page(request: Request):
    return templates.TemplateResponse("messages.html", {"request": request})


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "scheduler_running": scheduler_service.scheduler.running,
        "scheduled_jobs": len(scheduler_service.get_scheduler_jobs()),
        "ai_available": ai_service.get_status()["available"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
