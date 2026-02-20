"""
Task Executor Service - Handles actual task execution
"""
import asyncio
import subprocess
import requests
import tempfile
import os
import sys
import shutil
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

from app.models.schemas import TaskType

class TaskExecutor:
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
    async def execute(self, task_id: int, task_name: str, task_type: TaskType, 
                     config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task and return execution result"""
        start_time = time.time()
        
        try:
            if task_type == TaskType.HTTP:
                result = await self._execute_http(config)
            elif task_type == TaskType.SHELL:
                result = await self._execute_shell(config)
            elif task_type == TaskType.PYTHON:
                result = await self._execute_python(config)
            elif task_type == TaskType.BACKUP:
                result = await self._execute_backup(config)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            duration_ms = int((time.time() - start_time) * 1000)
            result["duration_ms"] = duration_ms
            result["completed_at"] = datetime.utcnow()
            
            # Log execution
            await self._log_execution(task_id, task_name, result)
            
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = {
                "status": "failed",
                "output": "",
                "error_message": str(e),
                "exit_code": -1,
                "duration_ms": duration_ms,
                "completed_at": datetime.utcnow()
            }
            await self._log_execution(task_id, task_name, result)
            return result
    
    async def _execute_http(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute HTTP request task"""
        url = config.get("url")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        body = config.get("body")
        timeout = config.get("timeout", 30)
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, data=body, timeout=timeout)
            elif method == "PUT":
                response = requests.put(url, headers=headers, data=body, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            output = f"Status: {response.status_code}\nHeaders: {dict(response.headers)}\nBody: {response.text[:2000]}"
            
            return {
                "status": "success" if response.status_code < 400 else "failed",
                "output": output,
                "error_message": None if response.status_code < 400 else f"HTTP {response.status_code}",
                "exit_code": response.status_code
            }
        except requests.RequestException as e:
            return {
                "status": "failed",
                "output": "",
                "error_message": f"Request failed: {str(e)}",
                "exit_code": -1
            }
    
    async def _execute_shell(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute shell command task"""
        command = config.get("command")
        working_dir = config.get("working_dir")
        timeout = config.get("timeout", 300)
        env_vars = config.get("env_vars", {})
        
        # Merge environment variables
        env = os.environ.copy()
        env.update(env_vars)
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")
            
            return {
                "status": "success" if process.returncode == 0 else "failed",
                "output": output,
                "error_message": error if error else None,
                "exit_code": process.returncode
            }
        except asyncio.TimeoutError:
            process.kill()
            return {
                "status": "failed",
                "output": "",
                "error_message": f"Command timed out after {timeout} seconds",
                "exit_code": -1
            }
    
    async def _execute_python(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python code task"""
        code = config.get("code")
        timeout = config.get("timeout", 300)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")
            
            return {
                "status": "success" if process.returncode == 0 else "failed",
                "output": output,
                "error_message": error if error else None,
                "exit_code": process.returncode
            }
        except asyncio.TimeoutError:
            process.kill()
            return {
                "status": "failed",
                "output": "",
                "error_message": f"Python script timed out after {timeout} seconds",
                "exit_code": -1
            }
        finally:
            os.unlink(temp_file)
    
    async def _execute_backup(self, config: Dict[str, Any]) -> Dict[str,
