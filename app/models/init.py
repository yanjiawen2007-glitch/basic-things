"""
Database models for Task Scheduler
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False)  # http, shell, python, backup
    cron_expression = Column(String(100), nullable=False)
    
    # Task configuration stored as JSON
    config = Column(JSON, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_running = Column(Boolean, default=False)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    
    # Notification settings
    notify_on_success = Column(Boolean, default=False)
    notify_on_failure = Column(Boolean, default=True)
    notification_email = Column(String(200), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

class TaskLog(Base):
    __tablename__ = "task_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False, index=True)
    task_name = Column(String(100), nullable=False)
    
    # Execution details
    status = Column(String(20), nullable=False)  # running, success, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Output
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    
    # Trigger info
    trigger_type = Column(String(20), default="scheduled")  # scheduled, manual, api

# Database setup
def init_db(db_path="./data/scheduler.db"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

SessionLocal = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
