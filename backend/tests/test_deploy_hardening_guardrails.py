from __future__ import annotations

import contextlib
import io
import json
import unittest
from pathlib import Path

from backend.app.config import GEMINI_OPENAI_BASE_URL, Settings
from backend.scripts import deploy_guard
from backend.scripts.run_migrations import list_migrations


class DeployHardeningGuardrailTests(unittest.TestCase):
    def test_deploy_guard_passes_for_current_release(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = deploy_guard.main([])
        self.assertEqual(code, 0, stderr.getvalue())
        self.assertIn("deploy hardening checks passed", stdout.getvalue())

    def test_migrations_have_deterministic_005_then_005b_order(self) -> None:
        migrations = [path.name for path in list_migrations(Path("backend/db/migrations"))]
        self.assertIn("005_tool_execution_native.sql", migrations)
        self.assertIn("005b_whatsapp_anti_blocking_guardrails.sql", migrations)
        self.assertLess(migrations.index("005_tool_execution_native.sql"), migrations.index("005b_whatsapp_anti_blocking_guardrails.sql"))
        self.assertNotIn("005_whatsapp_anti_blocking_guardrails.sql", migrations)

    def test_gemini_base_url_rejects_non_gemini_model(self) -> None:
        settings = Settings(
            app_env="production",
            openai_api_key="present",
            openai_model="gpt-5",
            openai_base_url=GEMINI_OPENAI_BASE_URL,
            autopilot_max_autofix_rounds=2,
            openai_timeout_seconds=30,
        )
        with self.assertRaisesRegex(ValueError, "Gemini"):
            settings.validate_ai_provider_alignment(require_explicit=False)

    def test_autopilot_round_budget_rejects_more_than_two_rounds(self) -> None:
        settings = Settings(autopilot_max_autofix_rounds=3, openai_timeout_seconds=30)
        with self.assertRaisesRegex(ValueError, "AUTOPILOT_MAX_AUTOFIX_ROUNDS"):
            settings.validate_ai_provider_alignment(require_explicit=False)

    def test_accept_all_ui_calls_autopilot_directly_with_progress(self) -> None:
        content = Path("frontend/features/bot-studio/create/AiSetupAssistant.tsx").read_text(encoding="utf-8")
        self.assertIn("const accept = async () =>", content)
        self.assertIn('const wired = await onAutopilot({ userDescription: description, intensity: "savage" });', content)
        self.assertIn("onClick={accept}", content)
        self.assertIn("Detectando industria...", content)
        self.assertIn("Generando setup completo...", content)
        self.assertIn("Validando...", content)
        self.assertNotIn('accept("accept")', content)

    def test_frontend_env_example_is_single_canonical_file(self) -> None:
        canonical = Path("frontend/.env.production.example")
        self.assertTrue(canonical.exists())
        self.assertFalse(Path("frontend/.env.example").exists())
        self.assertFalse(Path("frontend/.env.vercel.example").exists())
        content = canonical.read_text(encoding="utf-8")
        self.assertIn("canonical source of truth", content)
        self.assertIn("NEXT_PUBLIC_API_BASE_URL=", content)
        self.assertIn("API_INTERNAL_URL=", content)

    def test_render_proxy_and_three_workers_are_guarded(self) -> None:
        render_yaml = Path("render.yaml").read_text(encoding="utf-8")
        self.assertIn("- key: TRUST_PROXY_HEADERS\n        value: true", render_yaml)
        self.assertIn("- key: TRUSTED_PROXY_IPS\n        value: 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1/32,::1/128", render_yaml)
        self.assertIn("- key: WEB_CONCURRENCY\n        value: 3", render_yaml)
        bootstrap = Path("backend/scripts/bootstrap.sh").read_text(encoding="utf-8")
        self.assertIn("export WEB_CONCURRENCY=${WEB_CONCURRENCY:-3}", bootstrap)

    def test_ai_runtime_persistence_is_split_by_responsibility(self) -> None:
        self.assertLessEqual(len(Path("backend/app/ai_runtime/persistence.py").read_text(encoding="utf-8").splitlines()), 80)
        self.assertIn("def load_pipeline_context", Path("backend/app/ai_runtime/persistence_load.py").read_text(encoding="utf-8"))
        writer = Path("backend/app/ai_runtime/persistence_write.py").read_text(encoding="utf-8")
        self.assertIn("def persist_decision_outcome", writer)
        self.assertIn("def persist_pipeline_artifacts", writer)
        self.assertIn("def finalize_pipeline_run", writer)
        pipeline = Path("backend/app/ai_runtime/pipeline.py").read_text(encoding="utf-8")
        self.assertIn("from .persistence_load import load_pipeline_context", pipeline)
        self.assertIn("from .persistence_write import", pipeline)

    def test_vertical_fallback_ids_match_backend_profiles(self) -> None:
        index = json.loads(Path("frontend/app/lib/vertical-fallback/index.json").read_text(encoding="utf-8"))
        frontend_ids = {item["id"] for item in index}
        profile_files = {path.stem for path in Path("frontend/app/lib/vertical-fallback/profiles").glob("*.json")}
        self.assertEqual(frontend_ids, profile_files)
        self.assertTrue(Path("backend/scripts/export_vertical_profiles.py").exists())
        self.assertTrue(Path("scripts/sync-vertical-profiles.sh").exists())
        loader = Path("frontend/app/lib/vertical-fallback/index.ts").read_text(encoding="utf-8")
        self.assertIn("readFile", loader)
        self.assertIn("entry.file", loader)

    def test_release_gate_includes_ai_autopilot_endpoint(self) -> None:
        gate = Path("scripts/release_gate.py").read_text(encoding="utf-8")
        self.assertIn("/api/v1/onboarding/wizard/ai-autopilot", gate)
        router = Path("backend/app/api/routers/onboarding.py").read_text(encoding="utf-8")
        self.assertIn('@onboarding_router.post("/wizard/ai-autopilot"', router)


if __name__ == "__main__":
    unittest.main()
