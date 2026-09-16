from __future__ import annotations
import base64, io
from PIL import Image, ImageFilter, ImageOps

TARGET_SIZE = (720, 1280)
MAX_BINARY_BYTES = 3_200_000

def normalize_to_portrait(image_bytes: bytes) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as src:
        src = ImageOps.exif_transpose(src).convert("RGB")
        bg = src.copy()
        bg.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)
        scale = max(TARGET_SIZE[0] / bg.width, TARGET_SIZE[1] / bg.height)
        bw, bh = max(1, int(bg.width * scale)), max(1, int(bg.height * scale))
        bg = bg.resize((bw, bh), Image.Resampling.LANCZOS)
        left, top = (bw - TARGET_SIZE[0]) // 2, (bh - TARGET_SIZE[1]) // 2
        bg = bg.crop((left, top, left + TARGET_SIZE[0], top + TARGET_SIZE[1])).filter(ImageFilter.GaussianBlur(radius=28))
        fg = src.copy()
        fg.thumbnail((int(TARGET_SIZE[0] * 0.92), int(TARGET_SIZE[1] * 0.92)), Image.Resampling.LANCZOS)
        canvas = bg.copy()
        canvas.paste(fg, ((TARGET_SIZE[0] - fg.width) // 2, (TARGET_SIZE[1] - fg.height) // 2))
        for quality in (92, 88, 82, 76, 70):
            out = io.BytesIO()
            canvas.save(out, format="JPEG", quality=quality, optimize=True)
            data = out.getvalue()
            if len(data) <= MAX_BINARY_BYTES:
                return data
        raise ValueError("이미지를 Runway 입력 제한에 맞게 압축하지 못했습니다.")

def jpeg_bytes_to_data_uri(jpeg_bytes: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("ascii")
