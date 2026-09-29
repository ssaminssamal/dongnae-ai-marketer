from __future__ import annotations

import os
import tempfile

from gtts import gTTS


def generate_tts(
    text: str,
    lang: str = "ko",
) -> str:
    """
    입력 문장을 MP3 TTS 파일로 생성하고
    생성된 파일 경로를 반환한다.
    """

    text = text.strip()

    if not text:
        raise ValueError(
            "TTS 내레이션 문구가 비어 있습니다."
        )

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3",
    )

    temp_file.close()

    tts = gTTS(
        text=text,
        lang=lang,
        slow=False,
    )

    tts.save(
        temp_file.name
    )

    return temp_file.name


def remove_tts_file(
    path: str,
) -> None:
    """
    생성한 임시 TTS 파일을 삭제한다.
    """

    try:
        if path and os.path.exists(path):
            os.remove(path)

    except Exception:
        pass