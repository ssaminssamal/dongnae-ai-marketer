"""Temporary password-protected HTTPS preview. PC must remain on."""
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parent


def main():
    runtime=ROOT/'.runtime'; runtime.mkdir(exist_ok=True)
    binary=ROOT/'.tools'/('cloudflared.exe' if os.name=='nt' else 'cloudflared')
    if not binary.exists():
        raise SystemExit('먼저 python setup_public_preview.py를 실행하세요.')
    secret_path=runtime/'app_password'
    if not secret_path.exists(): secret_path.write_text(secrets.token_urlsafe(20),encoding='utf-8')
    password=secret_path.read_text(encoding='utf-8').strip()
    env=os.environ.copy(); env['DONGNAE_APP_PASSWORD']=password; env['PYTHONIOENCODING']='utf-8'
    app=None; tunnel=None
    try:
        with open(runtime/'gateway.log','a',encoding='utf-8') as app_log:
            app=subprocess.Popen([sys.executable,str(ROOT/'launch_app.py'),'--no-browser','--port','8503'],cwd=ROOT,env=env,stdout=app_log,stderr=app_log)
            client=requests.Session(); client.trust_env=False
            for attempt in range(60):
                if app.poll() is not None: raise RuntimeError('앱 실행 실패. .runtime/gateway.log 확인')
                try:
                    if client.get('http://127.0.0.1:8503/healthz',timeout=2).ok: break
                except requests.RequestException: pass
                time.sleep(.5)
            else: raise RuntimeError('앱 시작 시간 초과')
            tunnel=subprocess.Popen([str(binary),'tunnel','--url','http://127.0.0.1:8503','--no-autoupdate','--protocol','http2'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
            address=None
            for line in tunnel.stdout:
                match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
                if match:
                    address=match.group(0); break
                if tunnel.poll() is not None: break
            if not address: raise RuntimeError('HTTPS 미리보기 주소를 받지 못했습니다.')
            (runtime/'connection.txt').write_text('임시 동네AI 앱 주소: '+address+'\n접속 비밀번호: '+password+'\n\nPC와 이 실행 창이 켜져 있을 때만 접속됩니다. 주소는 다시 실행할 때 변경됩니다.\n',encoding='utf-8')
            print('HTTPS preview: '+address,flush=True)
            print('접속 비밀번호는 .runtime/connection.txt 파일에서 확인하세요.',flush=True)
            # Validate the authenticated app shell over HTTPS; never print the password.
            for attempt in range(20):
                try:
                    with requests.Session() as check:
                        login=check.post(address+'/login',data={'password':password},headers={'Origin':address},timeout=15)
                        if login.ok and '광고 편집 스튜디오' in login.text:
                            print('HTTPS login and app shell verified',flush=True); break
                except requests.RequestException: pass
                time.sleep(2)
            for line in tunnel.stdout:
                if 'error' in line.lower(): print('Tunnel connection status changed; check network.',flush=True)
    finally:
        for process in (tunnel,app):
            if process and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=8)
                except subprocess.TimeoutExpired: process.kill(); process.wait()


if __name__=='__main__': main()
