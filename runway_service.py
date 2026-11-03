from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from runwayml import RunwayML, TaskFailedError

from image_tools import normalize_to_portrait, jpeg_bytes_to_data_uri
from config import RUNWAY_MODELS, OUTPUT_RATIO


# =========================================================
# 환경 변수 로드
# =========================================================

load_dotenv()


# =========================================================
# 결과 객체
# =========================================================

@dataclass
class GenerationResult:
    ok: bool
    video_url: Optional[str] = None
    video_bytes: Optional[bytes] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
    attempts: int = 0


# =========================================================
# API Key
# =========================================================

def get_api_key() -> str:
    return os.getenv("RUNWAYML_API_SECRET", "").strip()


def api_key_configured() -> bool:
    key = get_api_key()

    return bool(
        key
        and key.startswith("key_")
    )


# =========================================================
# 예상 비용
# =========================================================

def estimated_cost(model: str, duration: int) -> dict:

    if model not in RUNWAY_MODELS:
        return {
            "credits": 0,
            "usd": 0
        }

    credits = (
        RUNWAY_MODELS[model]["credits_per_second"]
        * duration
    )

    return {
        "credits": credits,
        "usd": credits * 0.01
    }


# =========================================================
# 일반 오류 메시지 변환
# =========================================================

def _friendly_error(exc: Exception) -> tuple[str, str]:

    text = str(exc)
    lower = text.lower()

    # API Key
    if (
        "401" in lower
        or "unauthorized" in lower
        or "api key" in lower
    ):
        return (
            "AUTH",
            "API 키가 없거나 유효하지 않습니다. "
            "Streamlit Secrets 또는 .env의 RUNWAYML_API_SECRET을 확인하세요."
        )

    # 크레딧
    if (
        "402" in lower
        or "credit" in lower
        or "payment" in lower
        or "billing" in lower
    ):
        return (
            "CREDITS",
            "Runway 크레딧이 부족하거나 결제 설정이 필요합니다."
        )

    # 요청 제한
    if (
        "429" in lower
        or "rate limit" in lower
    ):
        return (
            "RATE_LIMIT",
            "Runway 요청이 너무 많습니다. 잠시 후 다시 시도하세요."
        )

    # 잘못된 요청
    if (
        "400" in lower
        or "bad request" in lower
        or "validation" in lower
    ):
        return (
            "BAD_REQUEST",
            "Runway가 입력을 거부했습니다. "
            f"이미지 또는 프롬프트를 확인하세요.\n\n{text[:400]}"
        )

    # 서버 오류
    if (
        "500" in lower
        or "502" in lower
        or "503" in lower
        or "internal server" in lower
    ):
        return (
            "SERVER",
            "Runway 서버에서 일시적인 오류가 발생했습니다. "
            "잠시 후 다시 시도하세요."
        )

    return (
        "UNKNOWN",
        text[:500]
    )


# =========================================================
# Runway Task 실패 분석
# =========================================================

def _task_failure_text(exc: TaskFailedError) -> str:

    detail = getattr(
        exc,
        "task_details",
        None
    )

    if detail is not None:
        return str(detail)

    return str(exc)


def _is_retryable_task_failure(text: str) -> bool:
    """
    Runway 내부 생성 오류일 경우에만 자동 재시도.

    인증/결제/입력 문제는 재시도해도 해결되지 않으므로
    자동 재시도하지 않는다.
    """

    upper = text.upper()

    retry_codes = [
        "INTERNAL.BAD_OUTPUT.CODE01",
        "INTERNAL.BAD_OUTPUT",
    ]

    return any(
        code in upper
        for code in retry_codes
    )


# =========================================================
# Prompt 정리
# =========================================================

def _prepare_prompt(prompt: str) -> str:

    if not prompt:
        raise ValueError(
            "영상 프롬프트가 비어 있습니다."
        )

    prompt = prompt.strip()

    if not prompt:
        raise ValueError(
            "영상 프롬프트가 비어 있습니다."
        )

    # Runway promptText 1000자 제한 대비
    # 여유 있게 950자로 제한
    if len(prompt) > 950:
        prompt = prompt[:950].rstrip()

    return prompt


# =========================================================
# 영상 다운로드
# =========================================================

def _download_video(url: str) -> bytes:

    response = requests.get(
        url,
        timeout=(15, 180)
    )

    response.raise_for_status()

    if not response.content:
        raise RuntimeError(
            "Runway 영상 URL은 반환됐지만 "
            "다운로드된 영상 데이터가 없습니다."
        )

    return response.content


# =========================================================
# Image → Video
# =========================================================

def generate_image_to_video(
    image_bytes: bytes,
    prompt: str,
    model: str = "gen4_turbo",
    duration: int = 5,
    max_attempts: int = 2,
) -> GenerationResult:

    # -----------------------------------------------------
    # 기본 검증
    # -----------------------------------------------------

    if not api_key_configured():
        return GenerationResult(
            ok=False,
            error_code="NO_KEY",
            message=(
                "Runway API 키가 설정되지 않았습니다. "
                "Streamlit Secrets 또는 .env의 RUNWAYML_API_SECRET을 확인하세요."
            )
        )

    if not image_bytes:
        return GenerationResult(
            ok=False,
            error_code="NO_IMAGE",
            message="업로드된 이미지가 없습니다."
        )

    if model not in RUNWAY_MODELS:
        return GenerationResult(
            ok=False,
            error_code="MODEL",
            message=f"지원하지 않는 모델입니다: {model}"
        )

    if duration not in (5, 10):
        return GenerationResult(
            ok=False,
            error_code="DURATION",
            message=(
                "현재 데모에서는 안정성을 위해 "
                "5초 또는 10초 영상만 지원합니다."
            )
        )

    # 과도한 자동 재시도 방지
    max_attempts = max(
        1,
        min(max_attempts, 2)
    )

    try:
        # -------------------------------------------------
        # 이미지 전처리
        # -------------------------------------------------

        prepared_image = normalize_to_portrait(
            image_bytes
        )

        data_uri = jpeg_bytes_to_data_uri(
            prepared_image
        )

        # -------------------------------------------------
        # Prompt 전처리
        # -------------------------------------------------

        prepared_prompt = _prepare_prompt(
            prompt
        )

        # -------------------------------------------------
        # Client 생성
        # -------------------------------------------------

        client = RunwayML(
            api_key=get_api_key()
        )

    except Exception as exc:

        code, msg = _friendly_error(exc)

        return GenerationResult(
            ok=False,
            error_code=code,
            message=msg
        )

    # =====================================================
    # 실제 생성
    # =====================================================

    last_failure = None

    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:
            # ---------------------------------------------
            # Runway 작업 생성
            # ---------------------------------------------

            task = (
                client.image_to_video
                .create(
                    model=model,
                    prompt_image=data_uri,
                    prompt_text=prepared_prompt,
                    ratio=OUTPUT_RATIO,
                    duration=duration,
                )
                .wait_for_task_output()
            )

            # ---------------------------------------------
            # output 확인
            # ---------------------------------------------

            output = getattr(
                task,
                "output",
                None
            )

            if not output:
                return GenerationResult(
                    ok=False,
                    error_code="EMPTY_OUTPUT",
                    message=(
                        "Runway 작업은 완료됐지만 "
                        "영상 URL이 반환되지 않았습니다."
                    ),
                    attempts=attempt
                )

            video_url = output[0]

            if not video_url:
                return GenerationResult(
                    ok=False,
                    error_code="EMPTY_URL",
                    message=(
                        "Runway가 빈 영상 URL을 반환했습니다."
                    ),
                    attempts=attempt
                )

            # ---------------------------------------------
            # 영상 다운로드
            # ---------------------------------------------

            video_bytes = _download_video(
                video_url
            )

            # ---------------------------------------------
            # 성공
            # ---------------------------------------------

            return GenerationResult(
                ok=True,
                video_url=video_url,
                video_bytes=video_bytes,
                attempts=attempt
            )

        # =================================================
        # Runway 생성 실패
        # =================================================

        except TaskFailedError as exc:

            failure_text = _task_failure_text(
                exc
            )

            last_failure = failure_text

            # ---------------------------------------------
            # INTERNAL.BAD_OUTPUT.CODE01
            # → 한 번 자동 재시도
            # ---------------------------------------------

            if (
                _is_retryable_task_failure(
                    failure_text
                )
                and attempt < max_attempts
            ):
                time.sleep(2)

                continue

            # ---------------------------------------------
            # 재시도 불가능 / 재시도도 실패
            # ---------------------------------------------

            return GenerationResult(
                ok=False,
                error_code="TASK_FAILED",
                message=(
                    "Runway 영상 생성 작업이 실패했습니다.\n\n"
                    f"{failure_text}"
                ),
                attempts=attempt
            )

        # =================================================
        # 기타 오류
        # =================================================

        except Exception as exc:

            code, msg = _friendly_error(
                exc
            )

            return GenerationResult(
                ok=False,
                error_code=code,
                message=msg,
                attempts=attempt
            )

    # 일반적으로 여기까지 오지 않지만 안전장치
    return GenerationResult(
        ok=False,
        error_code="RETRY_FAILED",
        message=(
            "Runway 영상 생성에 반복적으로 실패했습니다.\n\n"
            f"{last_failure or '알 수 없는 오류'}"
        ),
        attempts=max_attempts
    )


# =========================================================
# 영상 저장
# =========================================================

def save_video(
    video_bytes: bytes,
    directory: str = "outputs"
) -> str:

    from datetime import datetime

    if not video_bytes:
        raise ValueError(
            "저장할 영상 데이터가 없습니다."
        )

    output_dir = Path(directory)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    path = (
        output_dir
        / f"ad_{timestamp}.mp4"
    )

    path.write_bytes(
        video_bytes
    )

    return str(path)
