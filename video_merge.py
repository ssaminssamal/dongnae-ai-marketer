from __future__ import annotations

import os
import subprocess
import tempfile
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
from PIL import ImageColor
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
from tts_service import generate_tts, remove_tts_file

FONT_CANDIDATES = [r'C:\Windows\Fonts\malgunbd.ttf', r'C:\Windows\Fonts\malgun.ttf']
FONT_CANDIDATES += ['/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc']
FONT_CANDIDATES += ['/usr/share/fonts/truetype/nanum/NanumGothic.ttf', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
if os.getenv('DONGNAE_FONT_PATH'):
    FONT_CANDIDATES.insert(0, os.environ['DONGNAE_FONT_PATH'])


def _get_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    raise FileNotFoundError('한글 폰트를 찾을 수 없습니다. Linux에서는 fonts-nanum을 설치하거나 DONGNAE_FONT_PATH를 설정하세요.')


def _wrap_text(text, draw, font, max_width):
    lines = []
    for paragraph in text.splitlines():
        line = ''
        for char in paragraph:
            if line and draw.textlength(line + char, font=font) > max_width:
                lines.append(line.rstrip())
                line = char.lstrip()
            else:
                line += char
        lines.append(line)
    return '\n'.join(lines)


def _create_caption_image(text, video_size, font_size=46, brand_color=None):
    width, height = video_size
    image = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(image)
    margin = max(12, int(width * .07))
    padding = max(8, int(width * .025))
    size = max(12, int(font_size * width / 720))
    while True:
        font = _get_font(size)
        wrapped = _wrap_text(text, draw, font, width - 2 * (margin + padding))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=8, align='center')
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if th <= height * .30 or size <= 12:
            break
        size -= 2
    if th > height * .65:
        raise ValueError('자막이 너무 깁니다. 문구를 줄여 주세요.')
    x = (width - tw) / 2
    bottom = int(height * .84)
    top = bottom - th
    draw.rounded_rectangle((x-padding, top-padding, x+tw+padding, bottom+padding),
                           radius=padding, fill=(0, 0, 0, 180))
    if brand_color:
        draw.line((x,top-padding+3,x+tw,top-padding+3),fill=ImageColor.getrgb(brand_color)+(255,),width=3)
    draw.multiline_text((x-bbox[0], top-bbox[1]), wrapped, font=font,
                        fill='white', spacing=8, align='center')
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp:
        path = temp.name
    image.save(path)
    return path


def merge_video_bytes(video_bytes_list: List[bytes], output_dir: str = 'outputs',
                      final_captions: Optional[List[str]] = None,
                      narration_text: Optional[str] = None,
                      narration_audio: Optional[bytes] = None,
                      bgm_audio: Optional[bytes] = None,
                      bgm_volume: float = .18,
                      duck_music: bool = True,
                      brand_logo: Optional[bytes] = None,
                      brand_color: Optional[str] = None,
                      campaign_qr: Optional[bytes] = None) -> Tuple[bytes, str]:
    """Join scenes in order; captions span the ad. Never cut off narration."""
    if not video_bytes_list or any(not data for data in video_bytes_list):
        raise ValueError('합칠 영상이 없거나 비어 있는 장면이 있습니다.')
    if not 0 <= bgm_volume <= 1:
        raise ValueError('배경음악 음량은 0~1 사이여야 합니다.')
    if brand_color: ImageColor.getrgb(brand_color)
    has_music = bool(bgm_audio) and bgm_volume > 0
    folder = Path(output_dir).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    final_path = folder / f'final_ad_{datetime.now():%Y%m%d_%H%M%S_%f}.mp4'
    images = []
    tts_path = None
    try:
        with tempfile.TemporaryDirectory() as temp_dir, ExitStack() as resources:
            temp = Path(temp_dir)
            clips = []
            for i, data in enumerate(video_bytes_list):
                path = temp / f'scene_{i}.mp4'
                path.write_bytes(data)
                clip = resources.enter_context(VideoFileClip(str(path)))
                clips.append(clip.without_audio() if narration_text or narration_audio or has_music else clip)
            joined = concatenate_videoclips(clips, method='compose')
            resources.callback(joined.close)
            audio_path = None
            if narration_audio:
                audio_path = temp / 'narration.mp3'
                audio_path.write_bytes(narration_audio)
            elif narration_text and narration_text.strip():
                tts_path = generate_tts(narration_text.strip())
                audio_path = Path(tts_path)
            if audio_path:
                audio = resources.enter_context(AudioFileClip(str(audio_path)))
                if audio.duration > joined.duration:
                    freeze = ImageClip(joined.get_frame(max(0, joined.duration - 1/24))).with_duration(
                        audio.duration - joined.duration + .25)
                    resources.callback(freeze.close)
                    joined = concatenate_videoclips([joined, freeze], method='compose')
                    resources.callback(joined.close)
            captions = [s.strip() for s in (final_captions or []) if s and s.strip()]
            layers = [joined]
            for i, text in enumerate(captions):
                image = _create_caption_image(text, (int(joined.w), int(joined.h)),
                                              54 if i == len(captions)-1 else 44, brand_color)
                images.append(image)
                caption = ImageClip(image).with_start(i * joined.duration / len(captions)).with_duration(
                    joined.duration / len(captions))
                resources.callback(caption.close)
                layers.append(caption)
            for label,data in [('logo',brand_logo),('qr',campaign_qr)]:
                if not data: continue
                asset=temp/f'{label}.png'; asset.write_bytes(data)
                overlay=ImageClip(str(asset)).resized(width=max(40,int(joined.w*(.18 if label=='logo' else .32))))
                if label=='logo' and overlay.h>joined.h*.14: overlay=overlay.resized(height=int(joined.h*.14))
                overlay=overlay.with_position((int(joined.w-overlay.w-joined.w*.05),int(joined.h*(.06 if label=='logo' else .48))))
                if label=='qr': overlay=overlay.with_start(max(0,joined.duration-3)).with_duration(min(3,joined.duration))
                else: overlay=overlay.with_duration(joined.duration)
                resources.callback(overlay.close); layers.append(overlay)
            result = CompositeVideoClip(layers, size=joined.size) if len(layers)>1 else joined
            if len(layers)>1:
                resources.callback(result.close)
            silent_path = temp / 'picture.mp4'
            external_audio = bool(audio_path) or has_music
            result.write_videofile(str(silent_path if external_audio else final_path),
                                   codec='libx264', fps=24, audio=not external_audio,
                                   audio_codec='aac', temp_audiofile=str(temp / 'source.m4a'),
                                   ffmpeg_params=['-pix_fmt','yuv420p','-movflags','+faststart'], logger=None)
            if external_audio:
                command = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-i', str(silent_path)]
                filters = []
                if audio_path:
                    command += ['-i', str(audio_path)]
                    filters += [f'[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,apad,atrim=duration={result.duration},asetpts=PTS-STARTPTS[voice]']
                if has_music:
                    music_path = temp/'music.audio'
                    music_path.write_bytes(bgm_audio)
                    command += ['-stream_loop','-1','-i',str(music_path)]
                    music_index = 2 if audio_path else 1
                    filters += [f'[{music_index}:a]volume={bgm_volume},apad,atrim=duration={result.duration},asetpts=PTS-STARTPTS,afade=t=in:d=0.35,afade=t=out:st={max(0,result.duration-.7)}:d=0.7[music]']
                if audio_path and has_music:
                    if duck_music:
                        filters += ['[voice]asplit=2[spoken][side]',
                            '[music][side]sidechaincompress=threshold=0.025:ratio=6:attack=20:release=450[ducked]',
                            '[spoken][ducked]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.95:level=false[out]']
                    else:
                        filters += ['[voice][music]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.95:level=false[out]']
                else:
                    filters += [('[voice]' if audio_path else '[music]')+'alimiter=limit=0.95:level=false[out]']
                command += ['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[out]',
                            '-c:v','copy','-c:a','aac','-b:a','192k','-ar','44100',
                            '-t',str(result.duration),'-movflags','+faststart',str(final_path)]
                process = subprocess.run(command, capture_output=True)
                if process.returncode:
                    raise RuntimeError('음성·배경음악 결합 실패: ' + process.stderr.decode('utf-8', 'replace')[-1500:])
            with VideoFileClip(str(final_path)) as check:
                if abs(check.duration - result.duration) > .2:
                    raise RuntimeError('최종 영상 길이 검증 실패')
                if external_audio and check.audio is None:
                    raise RuntimeError('최종 영상에 오디오 트랙이 없습니다.')
            return final_path.read_bytes(), str(final_path)
    except Exception:
        final_path.unlink(missing_ok=True)
        raise
    finally:
        for image in images:
            Path(image).unlink(missing_ok=True)
        if tts_path:
            remove_tts_file(tts_path)
