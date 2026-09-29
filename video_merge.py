from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

from tts_service import generate_tts, remove_tts_file


# =========================================================
# 한글 폰트
# =========================================================

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\malgunbd.ttf",
    r"C:\Windows\Fonts\malgun.ttf",
]


def _get_font(size: int):

    for font_path in FONT_CANDIDATES:

        if os.path.exists(font_path):

            return ImageFont.truetype(
                font_path,
                size
            )

    raise FileNotFoundError(
        "한글 폰트를 찾을 수 없습니다."
    )


# =========================================================
# 자막 PNG 생성
# =========================================================

def _create_caption_image(
    text: str,
    video_size: Tuple[int, int],
    font_size: int = 46,
) -> str:

    width, height = video_size

    image = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(image)

    font = _get_font(
        font_size
    )

    bbox = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        spacing=8,
        align="center",
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (
        width - text_width
    ) // 2

    y = int(
        height * 0.72
    )

    padding_x = 30
    padding_y = 20

    draw.rounded_rectangle(
        (
            max(20, x - padding_x),
            y - padding_y,
            min(
                width - 20,
                x + text_width + padding_x
            ),
            y + text_height + padding_y,
        ),
        radius=20,
        fill=(0, 0, 0, 170),
    )

    draw.multiline_text(
        (x, y),
        text,
        font=font,
        fill=(255, 255, 255, 255),
        spacing=8,
        align="center",
    )

    temp_file = (
        tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".png",
        )
    )

    temp_file.close()

    image.save(
        temp_file.name
    )

    return temp_file.name


# =========================================================
# 마지막 장면에 자막 삽입
# =========================================================

def _add_final_scene_captions(
    clip,
    captions: List[str],
):

    captions = [
        text.strip()
        for text in captions
        if text and text.strip()
    ]

    if not captions:
        return clip, []

    width = int(clip.w)
    height = int(clip.h)

    duration = float(
        clip.duration
    )

    caption_duration = (
        duration
        / len(captions)
    )

    layers = [clip]

    image_paths = []

    for index, text in enumerate(
        captions
    ):

        font_size = (
            54
            if index == len(captions) - 1
            else 44
        )

        image_path = (
            _create_caption_image(
                text,
                (width, height),
                font_size,
            )
        )

        image_paths.append(
            image_path
        )

        start_time = (
            index
            * caption_duration
        )

        text_clip = (
            ImageClip(image_path)
            .with_start(start_time)
            .with_duration(
                caption_duration
            )
            .with_position((0, 0))
        )

        layers.append(
            text_clip
        )

    result = CompositeVideoClip(
        layers,
        size=(width, height),
    )

    return result, image_paths


# =========================================================
# 영상 합치기 + 자막 + TTS
# =========================================================

def merge_video_bytes(
    video_bytes_list: List[bytes],
    output_dir: str = "outputs",
    final_captions: Optional[List[str]] = None,
    narration_text: Optional[str] = None,
) -> Tuple[bytes, str]:

    if not video_bytes_list:

        raise ValueError(
            "합칠 영상이 없습니다."
        )

    output_folder = Path(
        output_dir
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_video_paths = []

    caption_image_paths = []

    clips = []

    final_clip = None

    narration_clip = None

    tts_path = None

    try:

        # -----------------------------------------
        # bytes → 임시 MP4
        # -----------------------------------------

        for index, video_bytes in enumerate(
            video_bytes_list,
            start=1,
        ):

            if not video_bytes:

                raise ValueError(
                    f"{index}번째 영상이 비어 있습니다."
                )

            temp_file = (
                tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=f"_scene_{index}.mp4",
                )
            )

            temp_file.write(
                video_bytes
            )

            temp_file.flush()

            temp_file.close()

            temp_video_paths.append(
                temp_file.name
            )

        # -----------------------------------------
        # 영상 로드
        # -----------------------------------------

        for path in temp_video_paths:

            clips.append(
                VideoFileClip(path)
            )

        # -----------------------------------------
        # 마지막 장면에 자막
        # -----------------------------------------

        if final_captions:

            last_index = (
                len(clips) - 1
            )

            caption_clip, image_paths = (
                _add_final_scene_captions(
                    clips[last_index],
                    final_captions,
                )
            )

            clips[last_index] = (
                caption_clip
            )

            caption_image_paths.extend(
                image_paths
            )

        # -----------------------------------------
        # 영상 합치기
        # -----------------------------------------

        final_clip = (
            concatenate_videoclips(
                clips,
                method="compose",
            )
        )

        # -----------------------------------------
        # TTS 내레이션
        # -----------------------------------------

        if (
            narration_text
            and narration_text.strip()
        ):

            tts_path = generate_tts(
                narration_text.strip()
            )

            narration_clip = (
                AudioFileClip(
                    tts_path
                )
            )

            # 영상보다 TTS가 길면 자름
            if (
                narration_clip.duration
                > final_clip.duration
            ):

                narration_clip = (
                    narration_clip.subclipped(
                        0,
                        final_clip.duration,
                    )
                )

            final_clip = (
                final_clip.with_audio(
                    narration_clip
                )
            )

        # -----------------------------------------
        # 최종 저장
        # -----------------------------------------

        timestamp = (
            datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
        )

        final_path = (
            output_folder
            / f"final_ad_{timestamp}.mp4"
        )

        final_clip.write_videofile(
            str(final_path),
            codec="libx264",
            audio_codec="aac",
            fps=24,
            logger=None,
        )

        merged_bytes = (
            final_path.read_bytes()
        )

        return (
            merged_bytes,
            str(final_path),
        )

    finally:

        # -----------------------------------------
        # 객체 정리
        # -----------------------------------------

        if final_clip is not None:

            try:
                final_clip.close()
            except Exception:
                pass

        if narration_clip is not None:

            try:
                narration_clip.close()
            except Exception:
                pass

        for clip in clips:

            try:
                clip.close()
            except Exception:
                pass

        # -----------------------------------------
        # TTS 임시파일 삭제
        # -----------------------------------------

        if tts_path:

            try:
                remove_tts_file(
                    tts_path
                )
            except Exception:
                pass

        # -----------------------------------------
        # 자막 이미지 삭제
        # -----------------------------------------

        for path in caption_image_paths:

            try:

                if os.path.exists(path):
                    os.remove(path)

            except Exception:
                pass

        # -----------------------------------------
        # 영상 임시파일 삭제
        # -----------------------------------------

        for path in temp_video_paths:

            try:

                if os.path.exists(path):
                    os.remove(path)

            except Exception:
                pass