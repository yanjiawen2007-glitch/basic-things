"""
Database models for Task Scheduler
"""
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

# 全局变量，由 init_db() 初始化
engine = None
SessionLocal = None


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


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Message source
    source = Column(String(50), nullable=False, default="email")  # email, manual, api
    source_account = Column(String(200), nullable=True)  # e.g., hr@weilan.com
    
    # Message content
    subject = Column(String(500), nullable=False)
    sender = Column(String(200), nullable=True)
    sender_name = Column(String(100), nullable=True)
    organization = Column(String(200), nullable=True)  # 来源单位
    contact_person = Column(String(100), nullable=True)  # 联系人
    
    # Full content
    body = Column(Text, nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)  # 是否已处理/创建任务
    
    # Related task
    task_id = Column(Integer, nullable=True)
    
    # Original message ID for deduplication
    message_id = Column(String(500), nullable=True, index=True)
    
    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db(db_path="./data/scheduler.db"):
    """
    初始化数据库
    设置全局变量 engine 和 SessionLocal
    """
    global engine, SessionLocal
    
    # 确保数据目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 创建引擎
    engine = create_engine(
        f"sqlite:///{db_path}", 
        connect_args={"check_same_thread": False}
    )
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 创建会话工厂
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 不返回任何值，SessionLocal 已通过全局变量设置


def get_db():
    """
    获取数据库会话生成器
    用于 FastAPI 依赖注入
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 公开接口
__all__ = [
    'Base',
    'Task',
    'TaskLog',
    'Message',
    'init_db',
    'get_db',
    'engine',
    'SessionLocal'
]
