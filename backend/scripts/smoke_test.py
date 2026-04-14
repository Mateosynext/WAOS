from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / 'app' / 'main.py',
    ROOT / 'app' / 'api' / 'routers' / 'webhooks.py',
    ROOT / 'db' / 'schema.sql',
    ROOT / 'requirements.txt',
]
missing = [str(x) for x in REQUIRED if not x.exists()]
if missing:
    raise SystemExit('Missing backend runtime smoke targets:\n' + '\n'.join(missing))

summary = {
    'ok': True,
    'required_files': [str(x.relative_to(ROOT)) for x in REQUIRED],
}
print(json.dumps(summary, indent=2, ensure_ascii=False))
