"""Free, on-device Korean speech. No cloud synthesis or API key."""
from functools import lru_cache
from pathlib import Path
import os
import tempfile
import threading

VOICES = {**{f'M{i}': f'남성 {i:02d}' for i in range(1,6)},
          **{f'F{i}': f'여성 {i:02d}' for i in range(1,6)}}
_lock = threading.RLock()


@lru_cache(maxsize=1)
def _engine():
    from supertonic import TTS
    model_dir = Path(os.getenv('DONGNAE_TTS_MODEL_DIR', str(Path(__file__).parent/'models'/'supertonic3')))
    # Install models explicitly through setup_free_tts.py; never download during an ad request.
    return TTS(model='supertonic-3', model_dir=model_dir, auto_download=False,
               intra_op_num_threads=4, inter_op_num_threads=1)


def generate_tts(text, lang='ko', *, voice_id='M1', speed=1.0, quality=8):
    text = text.strip()
    if not text or len(text)>3000:
        raise ValueError('내레이션은 1~3,000자로 입력해 주세요.')
    if voice_id not in VOICES or not .7<=float(speed)<=1.5 or quality not in (8,12):
        raise ValueError('목소리와 속도·품질 설정을 확인해 주세요.')
    path = None
    try:
        with _lock:
            engine = _engine()
            wav,_ = engine.synthesize(text,voice_style=engine.get_voice_style(voice_id),lang=lang,
                                      speed=float(speed),total_steps=quality,verbose=False)
            with tempfile.NamedTemporaryFile(delete=False,suffix='.wav') as temp:
                path = temp.name
            engine.save_audio(wav,path)
        if Path(path).stat().st_size<=44:
            raise RuntimeError('생성된 음성 파일이 비어 있습니다.')
        return path
    except (ImportError,FileNotFoundError) as error:
        remove_tts_file(path)
        raise RuntimeError('무료 음성 모델 설치가 필요합니다. setup_free_tts.py를 실행해 주세요.') from error
    except Exception:
        remove_tts_file(path)
        raise


def remove_tts_file(path):
    if path:
        Path(path).unlink(missing_ok=True)
