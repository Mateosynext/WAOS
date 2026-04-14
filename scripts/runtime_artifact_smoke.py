#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


def fetch(url: str) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        return resp.getcode(), data


def resolve_root(base: Path) -> Path:
    children = [child for child in base.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description='Extract a runtime zip and perform a smoke start against the artifact itself.')
    parser.add_argument('runtime_zip')
    parser.add_argument('--report')
    args = parser.parse_args()

    runtime_zip = Path(args.runtime_zip).resolve()
    temp_dir = Path(tempfile.mkdtemp(prefix='waos-runtime-smoke-'))
    proc = None
    try:
        with zipfile.ZipFile(runtime_zip, 'r') as zf:
            zf.extractall(temp_dir)
        root = resolve_root(temp_dir)
        db_path = temp_dir / 'smoke.db'
        env = os.environ.copy()
        env.update({
            'PYTHONPATH': str(root),
            'APP_ENV': 'test',
            'ALLOW_SQLITE_FOR_TESTS': 'true',
            'STRICT_SECURITY_STARTUP': 'false',
            'DATABASE_URL': f'sqlite:///{db_path}',
            'APP_SECRET': 'x' * 64,
            'SECRET_ENCRYPTION_KEY': 'y' * 64,
            'RUN_BOOTSTRAP_SEED': 'false',
        })
        proc = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8765'],
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        last_error = None
        for _ in range(60):
            if proc.poll() is not None:
                stdout, stderr = proc.communicate(timeout=5)
                raise RuntimeError(f'Runtime process exited early.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}')
            try:
                health_code, health = fetch('http://127.0.0.1:8765/healthz')
                ready_code, ready = fetch('http://127.0.0.1:8765/readyz')
                report = {
                    'ok': health_code == 200 and ready_code in {200, 503},
                    'root_directory': root.name,
                    'healthz': {'status_code': health_code, 'body': health},
                    'readyz': {'status_code': ready_code, 'body': ready},
                }
                if args.report:
                    Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
                print(json.dumps(report, indent=2, ensure_ascii=False))
                return 0 if report['ok'] else 1
            except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
                last_error = str(exc)
                time.sleep(1)
        raise RuntimeError(f'Runtime smoke timed out waiting for /healthz. Last error: {last_error}')
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())
