"""Use installed local voices, or lightweight online speech on hosted demos."""
import os
import tempfile
from pathlib import Path

from local_tts import remove_tts_file

_models = Path(os.getenv('DONGNAE_TTS_MODEL_DIR', str(Path(__file__).parent / 'models' / 'supertonic3')))
TTS_BACKEND = os.getenv('DONGNAE_TTS_BACKEND', 'local' if _models.is_dir() else 'gtts').lower()
if TTS_BACKEND not in ('local', 'gtts'):
    raise ValueError('DONGNAE_TTS_BACKEND must be local or gtts')

if TTS_BACKEND == 'local':
    from local_tts import VOICES, generate_tts
else:
    VOICES = {'default': '한국어 기본 음성'}

    def generate_tts(text, lang='ko', *, voice_id='default', speed=1.0, quality=8):
        from gtts import gTTS
        text = text.strip()
        if not text or len(text) > 3000:
            raise ValueError('내레이션은 1~3,000자로 입력해 주세요.')
        path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp:
                path = temp.name
            gTTS(text=text, lang=lang, timeout=(10, 60)).save(path)
            if Path(path).stat().st_size == 0:
                raise RuntimeError('생성된 음성 파일이 비어 있습니다.')
            return path
        except Exception as error:
            remove_tts_file(path)
            raise RuntimeError('음성 서비스에 연결할 수 없습니다. 잠시 후 다시 시도하거나 음성 파일을 업로드해 주세요.') from error
