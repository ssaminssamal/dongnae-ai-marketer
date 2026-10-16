"""ElevenLabs TTS. No credentials are persisted by this module."""
import os
import re
import tempfile
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))
API_ROOT = 'https://api.elevenlabs.io'
MODELS = {'eleven_v4': 'Eleven v4 · 풍부한 표현', 'eleven_v3': 'Eleven v3 · 감정 표현',
          'eleven_multilingual_v2': 'Multilingual v2 · 안정적인 내레이션',
          'eleven_flash_v2_5': 'Flash v2.5 · 빠른 생성'}


def _key(api_key=None):
    key = (api_key or os.getenv('ELEVENLABS_API_KEY', '')).strip()
    if not key:
        raise ValueError('연결 설정에서 ElevenLabs API 키를 입력해 주세요.')
    return key


def _check(response):
    if response.ok:
        return
    messages = {401: 'ElevenLabs API 키를 확인해 주세요.',
        403: '선택한 음성·모델의 사용 권한과 API 키 권한을 확인해 주세요.',
        404: '음성을 찾지 못했습니다. 목소리 목록을 새로 불러와 주세요.',
        429: '음성 생성 한도에 도달했습니다. 계정 사용량을 확인해 주세요.',
        422: '음성 설정을 사용할 수 없습니다. 다른 모델이나 목소리를 선택해 주세요.'}
    raise RuntimeError(messages.get(response.status_code, f'음성 서비스 응답 오류 ({response.status_code})'))


def list_voices(api_key=None, page_token=None):
    params = {'page_size': 100, 'sort': 'name'}
    if page_token:
        params['next_page_token'] = page_token
    try:
        response = requests.get(f'{API_ROOT}/v2/voices', headers={'xi-api-key': _key(api_key)},
                                params=params, timeout=(10, 30))
        _check(response)
        payload = response.json()
        return payload.get('voices', []), payload.get('next_page_token') if payload.get('has_more') else None
    except requests.RequestException:
        raise RuntimeError('음성 서비스에 연결하지 못했습니다. 네트워크를 확인해 주세요.') from None


def generate_tts(text, lang='ko', *, api_key=None, voice_id=None, model_id=None, stability=.5, speed=1.0):
    text = text.strip()
    if not text or len(text) > 3000:
        raise ValueError('내레이션은 1~3,000자로 입력해 주세요.')
    key = _key(api_key)
    voice = (voice_id or os.getenv('ELEVENLABS_VOICE_ID', '')).strip()
    model = model_id or os.getenv('ELEVENLABS_MODEL_ID', 'eleven_v4')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', voice):
        raise ValueError('사용할 목소리를 선택하거나 Voice ID를 입력해 주세요.')
    if model not in MODELS or stability not in (0.0, .5, 1.0) or not .7 <= float(speed) <= 1.2:
        raise ValueError('음성 모델과 표현·속도 설정을 확인해 주세요.')
    settings = {'stability': stability, 'similarity_boost': .75}
    if model in ('eleven_multilingual_v2', 'eleven_flash_v2_5'):
        settings.update(speed=float(speed), use_speaker_boost=True)
    payload = {'text': text, 'model_id': model, 'voice_settings': settings}
    if model != 'eleven_multilingual_v2':
        payload['language_code'] = lang
    try:
        response = requests.post(f'{API_ROOT}/v1/text-to-speech/{voice}',
            headers={'xi-api-key': key, 'Accept': 'audio/mpeg'},
            params={'output_format': 'mp3_44100_128'}, json=payload, timeout=(10, 90))
        _check(response)
    except requests.RequestException:
        raise RuntimeError('음성 생성 연결이 끊겼습니다. 사용 내역을 확인한 뒤 다시 시도해 주세요.') from None
    if not response.content or 'audio/' not in response.headers.get('Content-Type', '').lower():
        raise RuntimeError('음성 서비스에서 유효한 오디오를 받지 못했습니다.')
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp:
            path = temp.name
            temp.write(response.content)
        return path
    except Exception:
        remove_tts_file(path)
        raise


def remove_tts_file(path):
    if path:
        Path(path).unlink(missing_ok=True)
