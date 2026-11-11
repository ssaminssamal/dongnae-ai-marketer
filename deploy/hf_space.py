"""Upload this repository to a Hugging Face Docker Space and set its secrets.

Used by .github/workflows/deploy-hf.yml. Can also be run by hand:
    HF_TOKEN=hf_xxx DONGNAE_APP_PASSWORD=... python deploy/hf_space.py
"""
from __future__ import annotations
import os
import shutil
import sys
import tempfile
from pathlib import Path
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
SKIP = {'.git', '.github', '.env', '.runtime', '.data', '.vendor', '.tools', 'outputs', 'models',
        'backups', 'work', 'node_modules', '__pycache__', '.venv'}
SKIP_SUFFIX = {'.bat', '.mp4', '.mp3', '.log', '.pyc', '.sqlite3'}

SPACE_README = """---
title: 동네AI 광고 스튜디오
emoji: 🎬
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 8503
pinned: false
---

# 동네AI 광고 스튜디오

사진으로 광고 장면을 만들고 한글 자막과 무료 로컬 TTS를 더해 세로 MP4로 저장합니다.
접속 비밀번호가 필요합니다. 아래 주소를 새 탭에서 바로 여세요(이 페이지 안의 미리보기 창에서는 로그인이 되지 않습니다).

{url}
"""


def staged_copy(target: Path) -> None:
    for item in ROOT.rglob('*'):
        rel = item.relative_to(ROOT)
        if any(part in SKIP for part in rel.parts) or item.suffix.lower() in SKIP_SUFFIX:
            continue
        if item.name.startswith('.env') and item.name != '.env.example':
            continue
        if item.suffix.lower() == '.wav' and rel.parts[:2] != ('assets', 'music'):
            continue
        dest = target / rel
        if item.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)


def main() -> int:
    token = os.getenv('HF_TOKEN', '').strip()
    password = os.getenv('DONGNAE_APP_PASSWORD', '').strip()
    if not token:
        print('HF_TOKEN이 없습니다. Hugging Face에서 Write 권한 토큰을 만들어 넣어 주세요.')
        return 1
    if len(password) < 12:
        print('DONGNAE_APP_PASSWORD를 12자 이상으로 설정해 주세요.')
        return 1
    api = HfApi(token=token)
    owner = os.getenv('HF_SPACE_OWNER', '').strip() or api.whoami()['name']
    name = os.getenv('HF_SPACE_NAME', '').strip() or 'dongnae-ai-marketer'
    repo_id = f'{owner}/{name}'
    url = f"https://{owner.lower().replace('_', '-').replace('.', '-')}-{name.lower().replace('_', '-').replace('.', '-')}.hf.space"

    # The Space must be public so other people can open it; the app's own password protects it.
    api.create_repo(repo_id, repo_type='space', space_sdk='docker', exist_ok=True, private=False)
    api.add_space_secret(repo_id, 'DONGNAE_APP_PASSWORD', password)
    runway = os.getenv('RUNWAYML_API_SECRET', '').strip()
    if runway:
        api.add_space_secret(repo_id, 'RUNWAYML_API_SECRET', runway)

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        staged_copy(stage)
        (stage / 'README.md').write_text(SPACE_README.format(url=url), encoding='utf-8')
        if (ROOT / 'README.md').exists():
            shutil.copy2(ROOT / 'README.md', stage / 'PROJECT_README.md')
        api.upload_folder(repo_id=repo_id, repo_type='space', folder_path=stage,
                          commit_message=os.getenv('DEPLOY_MESSAGE', 'Deploy from GitHub'),
                          delete_patterns=['*'])
    print(f'배포 요청 완료: https://huggingface.co/spaces/{repo_id}')
    print(f'앱 주소(이용자에게 공유): {url}')
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as fh:
            fh.write(f'### 배포 완료\n\n- 앱 주소: {url}\n- Space 관리: https://huggingface.co/spaces/{repo_id}\n'
                     '- 첫 빌드는 음성 모델 다운로드 때문에 10~15분 정도 걸립니다.\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
