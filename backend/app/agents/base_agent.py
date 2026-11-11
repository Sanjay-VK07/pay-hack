import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.config import settings

def utcnow():
    return datetime.now(timezone.utc)

class BaseAgent:
    name: str = "BaseAgent"
    stage: str = "BASE"
    description: str = "Base agent specification"

    def __init__(self):
        self.ai_provider = settings.AI_PROVIDER
        self.has_llm = bool(settings.GEMINI_API_KEY or settings.OPENAI_API_KEY)

    def _call_llm_if_available(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Attempts structured JSON response from Gemini or OpenAI if configured.
        Returns None if not configured or if in Demo Mode.
        """
        if settings.DEMO_MODE and not (settings.GEMINI_API_KEY or settings.OPENAI_API_KEY):
            return None

        # Gemini API Provider
        if settings.GEMINI_API_KEY:
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\nTask:\n{prompt}\n\nReturn ONLY a valid JSON object."}]}],
                    "generationConfig": {"response_mime_type": "application/json"}
                }
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    text_content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text_content)
            except Exception:
                pass

        # OpenAI API Provider
        if settings.OPENAI_API_KEY:
            try:
                import requests
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"{prompt}\nReturn JSON format only."}
                    ],
                    "response_format": {"type": "json_object"}
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
                if resp.status_code == 200:
                    text_content = resp.json()["choices"][0]["message"]["content"]
                    return json.loads(text_content)
            except Exception:
                pass

        return None

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standard agent execution wrapper measuring execution time,
        capturing status, and handling deterministic fallback with explicit labelling.
        """
        start_time = utcnow()
        t0 = time.time()
        
        try:
            output = self._remove_uncalibrated_confidence(self.run(inputs))
            duration_ms = round((time.time() - t0) * 1000, 2)
            
            # Label provider mode
            is_llm = output.get("is_llm_generated", False)
            provider_label = "LLM_ASSISTED" if is_llm else "DETERMINISTIC_EXPERT_AGENT"
            
            return {
                "agent_name": self.name,
                "stage": self.stage,
                "status": "COMPLETED",
                "started_at": start_time.isoformat(),
                "completed_at": utcnow().isoformat(),
                "duration_ms": duration_ms,
                "provider_mode": provider_label,
                "summary": output.get("summary", ""),
                "findings": output.get("findings", {}),
                "output_json": output,
                "error": None
            }
        except Exception as e:
            return {
                "agent_name": self.name,
                "stage": self.stage,
                "status": "FAILED",
                "started_at": start_time.isoformat(),
                "completed_at": utcnow().isoformat(),
                "duration_ms": round((time.time() - t0) * 1000, 2),
                "provider_mode": "ERROR",
                "summary": f"Execution error in {self.name}: {str(e)}",
                "findings": {},
                "output_json": {},
                "error": str(e)
            }

    @classmethod
    def _remove_uncalibrated_confidence(cls, value: Any) -> Any:
        """Avoid persisting model-self-reported or hard-coded confidence as calibrated evidence."""
        if isinstance(value, dict):
            return {
                key: cls._remove_uncalibrated_confidence(item)
                for key, item in value.items()
                if key.lower() not in {"confidence", "confidence_score"}
            }
        if isinstance(value, list):
            return [cls._remove_uncalibrated_confidence(item) for item in value]
        return value

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
