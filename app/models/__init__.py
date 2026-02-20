""" Database models for Task Scheduler """

import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

engine = None
SessionLocal = None


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    config = Column(JSON, default=lambda: dict)
    is_active = Column(Boolean, default=True)
    is_running = Column(Boolean, default=False)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    notify_on_success = Column(Boolean, default=False)
    notify_on_failure = Column(Boolean, default=True)
    notification_email = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)


class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    task_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    trigger_type = Column(String(20), default="scheduled")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, default="email")
    source_account = Column(String(200), nullable=True)
    subject = Column(String(500), nullable=False)
    sender = Column(String(200), nullable=True)
    sender_name = Column(String(100), nullable=True)
    organization = Column(String(200), nullable=True)
    contact_person = Column(String(100), nullable=True)
    body = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    message_id = Column(String(500), nullable=True, index=True)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db(db_path="./data/scheduler.db"):
    global engine, SessionLocal
    
    db_dir = os.path.dirname(db_path) or "."
    os.makedirs(db_dir, exist_ok=True)
    
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False}
    )
    
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    'Base',
    'Task',
    'TaskLog',
    'Message',
    'init_db',
    'get_db',
]
