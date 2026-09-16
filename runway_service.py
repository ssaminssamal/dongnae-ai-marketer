from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import requests
from dotenv import load_dotenv
from runwayml import RunwayML, TaskFailedError
from image_tools import normalize_to_portrait, jpeg_bytes_to_data_uri
from config import RUNWAY_MODELS, OUTPUT_RATIO

load_dotenv()

@dataclass
class GenerationResult:
    ok: bool
    video_url: Optional[str] = None
    video_bytes: Optional[bytes] = None
    error_code: Optional[str] = None
    message: Optional[str] = None

def get_api_key() -> str:
    return os.getenv("RUNWAYML_API_SECRET", "").strip()

def api_key_configured() -> bool:
    key = get_api_key()
    return bool(key and key.startswith("key_"))

def estimated_cost(model: str, duration: int) -> dict:
    credits = RUNWAY_MODELS[model]["credits_per_second"] * duration
    return {"credits": credits, "usd": credits * 0.01}

def _friendly_error(exc: Exception) -> tuple[str, str]:
    text, lower = str(exc), str(exc).lower()
    if "401" in lower or "unauthorized" in lower or "api key" in lower:
        return "AUTH", "API 키가 없거나 유효하지 않습니다. .env의 RUNWAYML_API_SECRET을 확인하세요."
    if "402" in lower or "credit" in lower or "payment" in lower or "billing" in lower:
        return "CREDITS", "Runway 크레딧이 부족하거나 결제 설정이 필요합니다."
    if "429" in lower or "rate limit" in lower:
        return "RATE_LIMIT", "요청이 너무 많습니다. 잠시 후 다시 시도하세요."
    if "400" in lower or "bad request" in lower:
        return "BAD_REQUEST", f"Runway가 입력을 거부했습니다. 이미지/프롬프트를 확인하세요. ({text[:250]})"
    return "UNKNOWN", text[:500]

def generate_image_to_video(image_bytes: bytes, prompt: str, model: str = "gen4_turbo", duration: int = 5) -> GenerationResult:
    if not api_key_configured():
        return GenerationResult(False, error_code="NO_KEY", message="Runway API 키가 설정되지 않았습니다.")
    if model not in RUNWAY_MODELS:
        return GenerationResult(False, error_code="MODEL", message=f"지원하지 않는 모델입니다: {model}")
    if duration not in (5, 10):
        return GenerationResult(False, error_code="DURATION", message="이 데모에서는 안정성을 위해 5초 또는 10초만 사용합니다.")
    try:
        prepared = normalize_to_portrait(image_bytes)
        data_uri = jpeg_bytes_to_data_uri(prepared)
        client = RunwayML(api_key=get_api_key())
        task = client.image_to_video.create(
            model=model,
            prompt_image=data_uri,
            prompt_text=prompt,
            ratio=OUTPUT_RATIO,
            duration=duration,
        ).wait_for_task_output()
        if not getattr(task, "output", None):
            return GenerationResult(False, error_code="EMPTY_OUTPUT", message="Runway 작업은 완료됐지만 영상 URL이 반환되지 않았습니다.")
        url = task.output[0]
        response = requests.get(url, timeout=180)
        response.raise_for_status()
        return GenerationResult(True, video_url=url, video_bytes=response.content)
    except TaskFailedError as exc:
        detail = getattr(exc, "task_details", None)
        return GenerationResult(False, error_code="TASK_FAILED", message=f"Runway 영상 생성 작업이 실패했습니다. {detail or str(exc)}")
    except Exception as exc:
        code, msg = _friendly_error(exc)
        return GenerationResult(False, error_code=code, message=msg)

def save_video(video_bytes: bytes, directory: str = "outputs") -> str:
    from datetime import datetime
    Path(directory).mkdir(parents=True, exist_ok=True)
    path = Path(directory) / f"ad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    path.write_bytes(video_bytes)
    return str(path)
