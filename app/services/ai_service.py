"""
AI Service - Local LLM powered features using Ollama
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
import json

class AIService:
    """AI-powered features using local Ollama models"""
    
    def __init__(self, model_name: str = "llama3.2"):
        self.model = model_name
        self.common_patterns = {
            "每小时": "0 * * * *",
            "每天": "0 0 * * *",
            "每天早上9点": "0 9 * * *",
            "每天早上8点": "0 8 * * *",
            "每天晚上6点": "0 18 * * *",
            "每天晚上8点": "0 20 * * *",
            "每周一": "0 0 * * 1",
            "每周日": "0 0 * * 0",
            "每月1号": "0 0 1 * *",
            "每5分钟": "*/5 * * * *",
            "每10分钟": "*/10 * * * *",
            "每30分钟": "*/30 * * * *",
        }
        self._check_ollama()
    
    def _check_ollama(self):
        """Check if Ollama is running"""
        try:
            import ollama
            ollama.list()
            self.ollama_available = True
        except:
            self.ollama_available = False
            print("⚠️  Ollama 未运行，将使用规则引擎模式")
    
    def _call_llm(self, prompt: str, system_prompt: str = "") -> str:
        """Call local Ollama model"""
        if not self.ollama_available:
            return ""
        
        try:
            import ollama
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.3}
            )
            return response['message']['content']
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return ""
    
    def natural_language_to_cron(self, text: str) -> Dict[str, Any]:
        """Convert natural language to cron using LLM + rules"""
        text = text.strip()
        
        # 先尝试规则匹配（快速）
        for pattern, cron in self.common_patterns.items():
            if pattern in text:
                return {
                    "success": True,
                    "cron": cron,
                    "description": f"匹配到模式: {pattern}",
                    "next_runs": self._get_next_runs(cron),
                    "source": "rule"
                }
        
        # 使用 LLM 解析复杂描述
        if self.ollama_available:
            prompt = f"""将以下自然语言转换为 Linux Cron 表达式（5个字段：分 时 日 月 周）。

输入: "{text}"

只返回 JSON 格式，不要其他解释：
{{
    "cron": "0 9 * * *",
    "description": "每天早上9点执行",
    "confidence": 0.95
}}

如果无法解析，返回:
{{
    "cron": null,
    "description": "无法解析",
    "confidence": 0
}}"""
            
            try:
                result = self._call_llm(prompt)
                # 提取 JSON
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    if data.get("cron"):
                        return {
                            "success": True,
                            "cron": data["cron"],
                            "description": data.get("description", "AI解析结果"),
                            "next_runs": self._get_next_runs(data["cron"]),
                            "source": "llm",
                            "confidence": data.get("confidence", 0.8)
                        }
            except:
                pass
        
        # 回退到规则解析
        result = self._parse_complex_description(text)
        if result:
            return {
                "success": True,
                "cron": result["cron"],
                "description": result["description"],
                "next_runs": self._get_next_runs(result["cron"]),
                "source": "rule"
            }
        
        return {
            "success": False,
            "error": "无法解析该描述，请尝试: 每天、每小时、每周一、每5分钟等",
            "suggestions": list(self.common_patterns.keys())[:5]
        }
    
    def _parse_complex_description(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse complex time descriptions"""
        text = text.lower()
        
        # 匹配 "每X分钟"
        minute_match = re.search(r'每(\d+)分钟', text)
        if minute_match:
            minute = minute_match.group(1)
            return {
                "cron": f"*/{minute} * * * *",
                "description": f"每{minute}分钟执行一次"
            }
        
        # 匹配 "每X小时"
        hour_match = re.search(r'每(\d+)小时', text)
        if hour_match:
            hour = hour_match.group(1)
            return {
                "cron": f"0 */{hour} * * *",
                "description": f"每{hour}小时执行一次"
            }
        
        # 匹配 "每天X点"
        daily_match = re.search(r'每天.*?(\d+)[点:：]', text)
        if daily_match:
            hour = daily_match.group(1)
            return {
                "cron": f"0 {hour} * * *",
                "description": f"每天{hour}点执行"
            }
        
        # 匹配 "每周X"
        week_days = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 0, "天": 0}
        for day_name, day_num in week_days.items():
            if f"周{day_name}" in text or f"星期{day_name}" in text:
                time_match = re.search(r'(\d+)[点:：]', text)
                hour = time_match.group(1) if time_match else "0"
                return {
                    "cron": f"0 {hour} * * {day_num}",
                    "description": f"每周{day_name} {hour}点执行"
                }
        
        return None
    
    def _get_next_runs(self, cron: str, count: int = 5) -> List[str]:
        """Get next execution times for a cron expression"""
        try:
            from croniter import croniter
            itr = croniter(cron, datetime.now())
            return [itr.get_next(datetime).strftime("%Y-%m-%d %H:%M") for _ in range(count)]
        except:
            return []
    
    def analyze_error(self, error_message: str, task_type: str, output: str = "") -> Dict[str, Any]:
        """Analyze error using LLM + rules"""
        if not error_message:
            return {
                "category": "success",
                "suggestions": ["任务执行成功，无错误"],
                "confidence": 1.0,
                "source": "rule"
            }
        
        # 使用 LLM 分析复杂错误
        if self.ollama_available and len(error_message) > 50:
            prompt = f"""分析以下任务错误并提供解决方案。

任务类型: {task_type}
错误信息:
{error_message[:500]}

输出内容:
{output[:500] if output else "无"}

返回 JSON 格式:
{{
    "category": "错误类别",
    "root_cause": "根本原因",
    "solutions": ["解决方案1", "解决方案2", "解决方案3"],
    "prevention": "预防措施"
}}"""
            
            try:
                result = self._call_llm(prompt)
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    return {
                        "category": data.get("category", "unknown"),
                        "root_cause": data.get("root_cause", ""),
                        "suggestions": data.get("solutions", []),
                        "prevention": data.get("prevention", ""),
                        "confidence": 0.85,
                        "source": "llm"
                    }
            except:
                pass
        
        # 回退到规则分析
        return self._rule_based_error_analysis(error_message, task_type)
    
    def _rule_based_error_analysis(self, error_message: str, task_type: str) -> Dict[str, Any]:
        """Rule-based error analysis"""
        error_lower = error_message.lower()
        suggestions = []
        category = "unknown"
        
        if task_type == "http":
            if "timeout" in error_lower:
                category, suggestions = "timeout", ["增加超时时间", "检查服务器状态"]
            elif "404" in error_message:
                category, suggestions = "not_found", ["检查URL路径"]
            elif "401" in error_message or "403" in error_message:
                category, suggestions = "auth", ["检查认证信息"]
        
        elif task_type == "shell":
            if "command not found" in error_lower:
                category, suggestions = "command_not_found", ["检查命令是否安装"]
            elif "permission denied" in error_lower:
                category, suggestions = "permission", ["检查文件权限"]
        
        elif task_type == "python":
            if "module not found" in error_lower:
                category, suggestions = "import_error", ["安装缺失模块"]
            elif "syntaxerror" in error_lower:
                category, suggestions = "syntax_error", ["检查代码语法"]
        
        if not suggestions:
            suggestions = ["查看完整日志", "检查配置", "手动测试"]
        
        return {
            "category": category,
            "suggestions": suggestions,
            "confidence": 0.6,
            "source": "rule"
        }
    
    def suggest_task_config(self, description: str) -> Dict[str, Any]:
        """Suggest task configuration using LLM"""
        if self.ollama_available:
            prompt = f"""根据描述推荐任务配置。

描述: "{description}"

返回 JSON:
{{
    "task_type": "http|shell|python|backup",
    "task_name": "建议的任务名称",
    "cron": "0 9 * * *",
    "config": {{
        "关键配置项": "值"
    }},
    "tips": ["提示1", "提示2"]
}}"""
            
            try:
                result = self._call_llm(prompt)
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
        
        # 回退到规则
        return self._rule_based_suggestion(description)
    
    def _rule_based_suggestion(self, description: str) -> Dict[str, Any]:
        """Rule-based task suggestion"""
        desc_lower = description.lower()
        
        if any(kw in desc_lower for kw in ["http", "api", "url", "网站"]):
            return {
                "task_type": "http",
                "task_name": "HTTP请求任务",
                "cron": "0 */6 * * *",
                "config": {"url": "https://example.com", "method": "GET", "timeout": 30},
                "tips": ["修改URL为目标地址"]
            }
        elif any(kw in desc_lower for kw in ["备份", "backup"]):
            return {
                "task_type": "backup",
                "task_name": "数据备份任务",
                "cron": "0 2 * * *",
                "config": {"source_path": "/data", "destination_path": "/backup", "compress": True},
                "tips": ["修改源路径和目标路径"]
            }
        
        return {
            "task_type": "shell",
            "task_name": "定时任务",
            "cron": "0 9 * * *",
            "config": {"command": "echo 'Hello'", "timeout": 300},
            "tips": ["修改命令为您需要的操作"]
        }
    
    def chat_assistant(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """AI chat assistant using local LLM"""
        if self.ollama_available:
            system_prompt = """你是 TaskFlow 智能助手，帮助用户管理定时任务。
你可以：
1. 解析自然语言创建任务
2. 转换时间描述为 Cron 表达式
3. 分析任务错误
4. 推荐任务配置

回复简洁，用中文。"""
            
            context_str = f"\n上下文: {json.dumps(context, ensure_ascii=False)}" if context else ""
            prompt = f"用户: {message}{context_str}"
            
            response = self._call_llm(prompt, system_prompt)
            
            if response:
                return {
                    "type": "llm_response",
                    "response": response,
                    "source": "llm"
                }
        
        # 回退到规则
        return self._rule_based_chat(message)
    
    def _rule_based_chat(self, message: str) -> Dict[str, Any]:
        """Rule-based chat fallback"""
        msg_lower = message.lower()
        
        if any(kw in msg_lower for kw in ["创建", "新建", "添加"]):
            return {
                "type": "create_task",
                "response": "我来帮您创建任务。请描述：\n1. 任务要做什么？\n2. 什么时候执行？",
                "action": "open_task_modal"
            }
        elif any(kw in msg_lower for kw in ["cron", "定时", "表达式"]):
            return {
                "type": "cron_help",
                "response": "Cron 格式：分 时 日 月 周\n示例：0 9 * * *（每天9点）",
                "action": "show_cron_helper"
            }
        
        return {
            "type": "general",
            "response": "您好！我是 TaskFlow AI 助手。\n我可以帮您创建任务、解析 Cron 表达式、分析错误。\n请告诉我需要什么帮助？",
            "action": None
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get AI service status"""
        return {
            "ollama_running": self.ollama_available,
            "model": self.model if self.ollama_available else None,
            "mode": "llm" if self.ollama_available else "rule_only"
        }
