"""
AI Router - AI-powered API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional

from app.services.ai_service import AIService

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Global AI service
ai_service: AIService = None

def set_ai_service(service: AIService):
    global ai_service
    ai_service = service

@router.get("/status")
async def get_ai_status():
    """Get AI service status"""
    return ai_service.get_status()

@router.post("/natural-to-cron")
async def natural_to_cron(request: Dict[str, str]):
    """Convert natural language to cron expression"""
    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    result = ai_service.natural_language_to_cron(text)
    return result

@router.post("/analyze-error")
async def analyze_error(request: Dict[str, Any]):
    """Analyze task error and provide suggestions"""
    error_message = request.get("error_message", "")
    task_type = request.get("task_type", "shell")
    output = request.get("output", "")
    
    result = ai_service.analyze_error(error_message, task_type, output)
    return result

@router.post("/suggest-config")
async def suggest_config(request: Dict[str, str]):
    """Suggest task configuration based on description"""
    description = request.get("description", "")
    if not description:
        raise HTTPException(status_code=400, detail="Description is required")
    
    result = ai_service.suggest_task_config(description)
    return result

@router.post("/chat")
async def chat(request: Dict[str, Any]):
    """AI chat assistant"""
    message = request.get("message", "")
    context = request.get("context", {})
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    result = ai_service.chat_assistant(message, context)
    return result

@router.post("/query")
async def ai_query(request: Dict[str, Any]):
    """AI query endpoint (alias for chat)"""
    message = request.get("query", "")
    context = request.get("context", {})
    
    if not message:
        raise HTTPException(status_code=400, detail="Query is required")
    
    result = ai_service.chat_assistant(message, context)
    return {
        "success": result.get("type") != "error",
        "response": result.get("response", ""),
        "error": None
    }

@router.post("/generate-name")
async def generate_name(request: Dict[str, str]):
    """Generate task name from description"""
    description = request.get("description", "")
    if not description:
        raise HTTPException(status_code=400, detail="Description is required")
    
    name = ai_service.generate_task_name(description)
    return {"name": name}

@router.post("/parse-task")
async def parse_task(request: Dict[str, str]):
    """Parse natural language description into task configuration"""
    description = request.get("description", "")
    if not description:
        raise HTTPException(status_code=400, detail="Description is required")
    
    # Get task suggestion from AI
    suggestion = ai_service.suggest_task_config(description)
    
    # Get cron expression from natural language
    cron_result = ai_service.natural_language_to_cron(description)
    
    # Generate task name
    task_name = ai_service.generate_task_name(description)
    
    # Build complete task configuration
    task_config = {
        "name": suggestion.get("task_name", task_name),
        "description": description,
        "task_type": suggestion.get("task_type", "shell"),
        "cron_expression": cron_result.get("cron", "0 0 * * *"),
        "config": suggestion.get("config", {}),
        "is_enabled": True
    }
    
    return {
        "success": True,
        "task": task_config,
        "cron_description": cron_result.get("description", ""),
        "source": "llm" if ai_service.ollama_available else "rule"
    }
