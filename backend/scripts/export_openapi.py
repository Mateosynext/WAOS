from pathlib import Path
import json
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))

from backend.app.main import app  # noqa: E402

output = root / "docs" / "openapi.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {output}")
