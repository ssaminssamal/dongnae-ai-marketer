"""Start and stop the real optional Windows/Linux launcher over HTTP."""
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
import requests


class ServerSmoke(unittest.TestCase):
    def test_launcher_and_streamlit_health(self):
        root = Path(__file__).resolve().parents[1]
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = dict(os.environ, DONGNAE_APP_PASSWORD='', DONGNAE_TTS_BACKEND='gtts')
        with tempfile.TemporaryFile() as log:
            child = subprocess.Popen([sys.executable, str(root/'launch_app.py'), '--no-browser', '--port', str(port)],
                                     cwd=root, env=env, stdout=log, stderr=log)
            client = requests.Session()
            client.trust_env = False
            try:
                for _ in range(60):
                    if child.poll() is not None:
                        log.seek(0)
                        self.fail('Launcher exited before readiness: ' + log.read().decode('utf-8', 'replace')[-3000:])
                    try:
                        if client.get(f'http://127.0.0.1:{port}/healthz', timeout=1).ok:
                            break
                    except requests.RequestException:
                        pass
                    time.sleep(.25)
                else:
                    self.fail('Server startup timed out')
                self.assertEqual(client.get(f'http://127.0.0.1:{port}/studio/_stcore/health', timeout=5).status_code, 200)
                self.assertEqual(client.get(f'http://127.0.0.1:{port}/', timeout=5).status_code, 200)
                self.assertEqual(client.get(f'http://127.0.0.1:{port}/c/obsolete/map', timeout=5).status_code, 404)
            finally:
                client.close()
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
                else:
                    child.terminate()
                child.wait(timeout=15)
