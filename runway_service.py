"""Bounded API requests; retry existing tasks instead of creating paid duplicates."""
from dataclasses import dataclass
import time
from urllib.parse import urlsplit
import requests
from runwayml import RunwayML
from secrets_config import setting
from image_tools import normalize_to_portrait, jpeg_bytes_to_data_uri
from config import RUNWAY_MODELS, OUTPUT_RATIO

@dataclass
class GenerationResult:
    ok: bool
    video_url: str | None = None
    video_bytes: bytes | None = None
    error_code: str | None = None
    message: str | None = None
    attempts: int = 0


def get_api_key():
    return setting('RUNWAYML_API_SECRET')


def api_key_configured():
    return bool(get_api_key())


def estimated_cost(model, duration):
    credits = RUNWAY_MODELS.get(model, {}).get('credits_per_second', 0) * duration
    return dict(credits=credits, usd=credits*.01)


def _friendly_error(error):
    status = getattr(error, 'status_code', None)
    if status == 401:
        return 'AUTH', '영상 API 인증에 실패했습니다. 키를 확인해 주세요.'
    if status == 402:
        return 'CREDITS', '영상 API 잔액 또는 결제 설정을 확인해 주세요.'
    if status == 429:
        return 'RATE_LIMIT', '영상 API 요청 한도입니다. 잠시 후 같은 설정으로 재시도하세요.'
    return 'CONNECTION', '영상 API 연결이 중단됐습니다. 같은 설정으로 재시도하면 기존 작업을 이어서 확인합니다.'


def _download_video(url):
    if urlsplit(url).scheme != 'https':
        raise ValueError('Invalid video URL')
    # Only a GET is retried; never restart a paid generation on a download error.
    for attempt in range(2):
        try:
            with requests.get(url, timeout=(10, 60), stream=True) as response:
                response.raise_for_status()
                chunks, size = [], 0
                started = time.monotonic()
                for chunk in response.iter_content(1024*1024):
                    size += len(chunk)
                    if size > 100*1024*1024 or time.monotonic()-started > 120:
                        raise ValueError('Video download limit exceeded')
                    chunks.append(chunk)
                data = b''.join(chunks)
                if not data or b'ftyp' not in data[:32]:
                    raise ValueError('Invalid MP4 response')
                return data
        except requests.RequestException:
            if attempt:
                raise
            time.sleep(1)


def generate_image_to_video(image_bytes, prompt, model='gen4_turbo', duration=5,
                            *, task_state=None, poll_timeout=600):
    state = task_state if task_state is not None else {}
    if not api_key_configured():
        return GenerationResult(False, error_code='NO_KEY', message='RUNWAYML_API_SECRET을 설정해 주세요.')
    if not image_bytes or not prompt.strip() or model not in RUNWAY_MODELS or duration not in (5, 10):
        return GenerationResult(False, error_code='INPUT', message='사진·프롬프트·모델·장면 길이를 확인해 주세요.')
    client = None
    try:
        client = RunwayML(api_key=get_api_key(), timeout=60, max_retries=0)
        if not state.get('task_id'):
            task = client.image_to_video.create(model=model,
                prompt_image=jpeg_bytes_to_data_uri(normalize_to_portrait(image_bytes)),
                prompt_text=prompt.strip()[:950], ratio=OUTPUT_RATIO, duration=duration)
            state['task_id'] = task.id
        started = time.monotonic()
        while not state.get('video_url'):
            task = client.tasks.retrieve(state['task_id'])
            if task.status in ('FAILED', 'CANCELLED'):
                state.clear()
                return GenerationResult(False, error_code='TASK_FAILED', message='영상 작업이 실패하거나 취소됐습니다. 사진·연출을 확인하고 다시 시도하세요.', attempts=1)
            if task.status == 'SUCCEEDED':
                if not task.output:
                    return GenerationResult(False, error_code='EMPTY_OUTPUT', message='완료된 작업의 영상 주소가 없습니다.', attempts=1)
                state['video_url'] = task.output[0]
                break
            if time.monotonic()-started >= poll_timeout:
                return GenerationResult(False, error_code='TIMEOUT', message='영상 대기 시간이 초과됐습니다. 같은 설정으로 다시 누르면 기존 작업을 확인합니다.', attempts=1)
            time.sleep(3)
        data = _download_video(state['video_url'])
        return GenerationResult(True, video_url=state['video_url'], video_bytes=data, attempts=1)
    except Exception as error:
        code, message = _friendly_error(error)
        if not state.get('task_id') and code == 'CONNECTION':
            message = '영상 요청 접수 여부를 확인할 수 없습니다. Runway 작업 내역을 확인한 뒤 재시도하세요.'
        return GenerationResult(False, error_code=code, message=message, attempts=1)
    finally:
        if client:
            client.close()
