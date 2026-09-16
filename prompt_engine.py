from __future__ import annotations
from typing import Dict

STYLE_VISUAL = {
    "감성적": "warm cinematic lighting, gentle natural motion, slow controlled camera push-in, soft depth of field, intimate and authentic atmosphere",
    "유머러스": "playful energetic commercial pacing, expressive but realistic motion, dynamic camera movement, bright social-media-friendly visual rhythm",
    "트렌디": "modern vertical social media commercial, stylish lighting, clean composition, confident camera movement, premium short-form advertising aesthetic",
    "고급스러운": "premium cinematic commercial, restrained camera movement, sophisticated lighting, high-end brand film aesthetic, polished realistic materials",
    "친근한": "approachable neighborhood commercial, natural daylight, warm realistic movement, friendly and trustworthy atmosphere",
    "정보 전달형": "clean professional commercial, clear subject visibility, stable purposeful camera movement, realistic lighting, uncluttered background",
}

SUBJECT_MOTION = {
    "제품 / 상품": "Keep the product identity, shape, logo, packaging and colors consistent. Use subtle parallax, a gentle camera orbit or push-in, and realistic environmental motion. Do not invent extra product parts.",
    "메뉴 / 음식": "Keep the food visually faithful to the uploaded image. Use appetizing realistic micro-motion such as gentle steam only when plausible, subtle highlights, and a slow camera push-in. Do not add new ingredients.",
    "서비스": "Preserve the people, uniforms, tools and environment if present. Show professional atmosphere through subtle camera motion and natural environmental movement. Avoid body, hand and face distortions.",
    "매장 / 공간": "Preserve the room layout and key fixtures. Use a smooth cinematic reveal, subtle light movement and natural depth. Do not redesign the space.",
    "시술 / 포트폴리오": "Preserve the original result and the person's identity if present. Use subtle elegant motion and camera movement. Avoid changing facial features, body shape, haircut structure or the demonstrated result.",
    "수업 / 프로그램": "Preserve the learning environment and people if present. Create natural classroom or activity motion with a professional camera move. Avoid face and hand distortions.",
    "이벤트 / 프로모션": "Preserve the photographed venue, product or people. Create energetic but realistic movement suitable for a short promotional teaser.",
}

def build_runway_prompt(business_type: str, subject_type: str, subject_name: str, description: str, style: str, goal: str, analysis: Dict, unique_point: str = "") -> str:
    visual = STYLE_VISUAL[style]
    motion = SUBJECT_MOTION[subject_type]
    unique = unique_point.strip() or ", ".join(analysis["business_points"][:2])
    return f"""Create a polished vertical short-form advertisement from the provided image.

SUBJECT
- Business category: {business_type}
- Promotion type: {subject_type}
- Main subject: {subject_name}
- Description: {description}
- Key selling point: {unique}

AUDIENCE AND INTENT
- Local market: {analysis['location']} / {analysis['area_type']}
- Target audience: {analysis['target']}
- Advertising goal: {goal}

VISUAL DIRECTION
- Style: {style}
- Look: {visual}
- {motion}

CAMERA AND MOTION
Start from the uploaded image as the visual source of truth.
Create one coherent commercial shot with natural depth and purposeful movement.
Keep the main subject clearly recognizable throughout the video.
Use movement that matches the real-world subject and avoid impossible transformations.

STRICT CONSTRAINTS
Do not generate captions, logos, subtitles, prices, signs, watermarks or unreadable text inside the video.
Do not alter brand marks that already exist in the source image.
Do not add unrelated objects or people.
Prioritize realism, visual consistency and commercial usability.
""".strip()
