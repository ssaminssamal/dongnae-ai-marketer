"""Download cloudflared from its official GitHub release, verifying GitHub's SHA256."""
import hashlib
import os
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    name='cloudflared-windows-amd64.exe' if os.name=='nt' else 'cloudflared-linux-amd64'
    metadata=requests.get('https://api.github.com/repos/cloudflare/cloudflared/releases/latest',timeout=30)
    metadata.raise_for_status()
    asset=next(a for a in metadata.json()['assets'] if a['name']==name)
    checksum=asset.get('digest','')
    if not checksum.startswith('sha256:'): raise RuntimeError('다운로드 검증용 SHA256이 없어 설치를 중단합니다.')
    folder=ROOT/'.tools'; folder.mkdir(exist_ok=True)
    temp=folder/'cloudflared.download'
    try:
        digest=hashlib.sha256()
        with requests.get(asset['browser_download_url'],stream=True,timeout=(15,90)) as response:
            response.raise_for_status()
            with temp.open('wb') as output:
                for chunk in response.iter_content(1024*1024):
                    output.write(chunk); digest.update(chunk)
        if digest.hexdigest()!=checksum.split(':',1)[1]: raise RuntimeError('다운로드 SHA256 검증 실패')
        final=folder/('cloudflared.exe' if os.name=='nt' else 'cloudflared')
        temp.replace(final)
        if os.name!='nt': final.chmod(0o755)
        print('Official cloudflared installed and SHA256 verified:',metadata.json()['tag_name'])
    finally:
        temp.unlink(missing_ok=True)
