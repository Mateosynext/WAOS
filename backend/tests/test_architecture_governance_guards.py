from __future__ import annotations

import ast
import re
from pathlib import Path

from backend.app.migrations import MIGRATIONS


APP_DIR = Path(__file__).resolve().parents[1] / "app"
ROOT_DIR = APP_DIR.parents[0]
DB_DIR = ROOT_DIR / "db"
DDL_ALLOWLIST = {
    APP_DIR / "migrations.py",
    APP_DIR / "runtime_schema_migration.py",
    APP_DIR / "platform_schema_migration.py",
}
DDL_PATTERN = re.compile(
    r"\b(?:CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE|CREATE\s+INDEX|ADD\s+COLUMN|CREATE\s+TRIGGER|CREATE\s+OR\s+REPLACE\s+FUNCTION)\b",
    re.IGNORECASE,
)
NUMERIC_SQL_FILE_PATTERN = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")



def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open(encoding="utf-8"))



def test_schema_ddl_is_confined_to_migration_modules() -> None:
    offenders: list[str] = []
    for path in APP_DIR.rglob("*.py"):
        if path in DDL_ALLOWLIST:
            continue
        if DDL_PATTERN.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(ROOT_DIR)))
    assert offenders == []



def test_migrations_registry_is_unique_and_no_duplicate_functions_exist() -> None:
    migrations_path = APP_DIR / "migrations.py"
    module = ast.parse(migrations_path.read_text(encoding="utf-8"))
    function_names = [node.name for node in module.body if isinstance(node, ast.FunctionDef)]
    assert len(function_names) == len(set(function_names))
    versions = [migration.version for migration in MIGRATIONS]
    assert len(versions) == len(set(versions))



def test_generation_runtime_is_split_and_kept_small() -> None:
    generation_path = APP_DIR / "ai_runtime" / "generation.py"
    helper_modules = [
        APP_DIR / "ai_runtime" / "generation_context.py",
        APP_DIR / "ai_runtime" / "generation_language.py",
        APP_DIR / "ai_runtime" / "generation_heuristics.py",
        APP_DIR / "ai_runtime" / "generation_openai.py",
    ]
    for helper in helper_modules:
        assert helper.exists(), helper.name
    assert _line_count(generation_path) <= 220



def test_schema_governance_orchestrators_stay_small() -> None:
    assert _line_count(APP_DIR / "runtime_schema_migration.py") <= 220
    assert _line_count(APP_DIR / "platform_schema_migration.py") <= 80
    assert _line_count(APP_DIR / "schema_sql.py") <= 80



def test_schema_sql_is_split_into_numbered_domain_fragments() -> None:
    expected_dirs = {
        DB_DIR / "schema" / "runtime": 8,
        DB_DIR / "schema" / "platform": 3,
    }
    for directory, min_count in expected_dirs.items():
        files = sorted(path.name for path in directory.glob("*.sql"))
        assert len(files) >= min_count
        assert files == sorted(files)
        assert all(NUMERIC_SQL_FILE_PATTERN.match(name) for name in files)





FRONTEND_DIR = ROOT_DIR.parent / "frontend"
FRONTEND_COMPONENT_MAX_LINES = {
    FRONTEND_DIR / "app" / "components" / "ConversationComposer.tsx": 120,
    FRONTEND_DIR / "features" / "bot-studio" / "BotStudioRoute.tsx": 160,
    FRONTEND_DIR / "app" / "components" / "conversation-composer" / "ModePanels.tsx": 80,
    FRONTEND_DIR / "app" / "components" / "conversation-composer" / "modes" / "InteractiveModePanel.tsx": 140,
    FRONTEND_DIR / "app" / "client" / "sections" / "renderOperations.tsx": 100,
    FRONTEND_DIR / "app" / "client" / "sections" / "operations" / "renderOperationalForms.tsx": 110,
}

FRONTEND_EXPECTED_SPLITS = [
    FRONTEND_DIR / "app" / "components" / "conversation-composer" / "modes" / "BasicModePanels.tsx",
    FRONTEND_DIR / "features" / "bot-studio" / "BotStudioRoute.tsx",
    FRONTEND_DIR / "features" / "bot-studio" / "domain" / "wizardTypes.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "domain" / "flowConfig.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "domain" / "wizardProgressGuards.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "services" / "wizardApi.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "services" / "wizardPayloadBuilders.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "services" / "wizardReactiveData.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "server" / "loadBotStudioRoute.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "ui" / "flowUi.tsx",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "types.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "BotStudioFlowBody.tsx",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowController.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "flowActionDeps.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowActionHelpers.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowActions.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioCreateFlowActions.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioReconfigureFlowActions.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowNavigation.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowStateModel.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowTelemetry.ts",
    FRONTEND_DIR / "features" / "bot-studio" / "api" / "wizardEndpoints.ts",
    FRONTEND_DIR / "app" / "components" / "conversation-composer" / "modes" / "MediaModePanel.tsx",
    FRONTEND_DIR / "app" / "components" / "conversation-composer" / "modes" / "InteractiveModePanel.tsx",
    FRONTEND_DIR / "app" / "components" / "conversation-composer" / "modes" / "FlowModePanel.tsx",
    FRONTEND_DIR / "app" / "components" / "conversation-composer" / "modes" / "CommerceModePanel.tsx",
    FRONTEND_DIR / "app" / "components" / "conversation-composer" / "modes" / "MarkAsReadModePanel.tsx",
    FRONTEND_DIR / "app" / "client" / "sections" / "operations" / "renderOperationalAlerts.tsx",
    FRONTEND_DIR / "app" / "client" / "sections" / "operations" / "renderOperationalAvailability.tsx",
    FRONTEND_DIR / "app" / "client" / "sections" / "operations" / "renderOperationalForms.tsx",
    FRONTEND_DIR / "app" / "client" / "sections" / "operations" / "renderOperationalRecentCommands.tsx",
]

ROOT_MODULE_PACKAGES = [
    APP_DIR / "whatsapp_channel_runtime" / "implementation.py",
    APP_DIR / "whatsapp_delivery_truth" / "implementation.py",
    APP_DIR / "whatsapp_governance" / "implementation.py",
    APP_DIR / "voice_pipeline" / "implementation.py",
    APP_DIR / "knowledge_runtime" / "implementation.py",
    APP_DIR / "live_knowledge_runtime" / "implementation.py",
    APP_DIR / "vertical_domain_runtime" / "implementation.py",
    APP_DIR / "vertical_marketplace_runtime" / "implementation.py",
    APP_DIR / "vertical_transactions" / "implementation.py",
    APP_DIR / "verticals" / "implementation.py",
    APP_DIR / "vertical_10x" / "implementation.py",
    APP_DIR / "world_class" / "implementation.py",
    APP_DIR / "world_class_plus" / "implementation.py",
    APP_DIR / "payments_runtime" / "implementation.py",
    APP_DIR / "human_ops_runtime" / "implementation.py",
]


def test_backend_app_root_surface_area_keeps_shrinking() -> None:
    direct_root_modules = sorted(path for path in APP_DIR.glob("*.py"))
    assert len(direct_root_modules) <= 55
    for path in ROOT_MODULE_PACKAGES:
        assert path.exists(), str(path.relative_to(ROOT_DIR))

APPLICATION_SERVICE_MAX_LINES = {
    "operational_control_service.py": 140,
    "tool_execution_service.py": 80,
    "optimizer_service.py": 80,
    "integration_service.py": 160,
    "onboarding_service.py": 120,
    "outcomes_service.py": 120,
}

APPLICATION_SUPPORT_MAX_LINES = {
    "operational_control_support.py": 80,
    "tool_execution_support.py": 80,
    "optimizer_support.py": 80,
    "operational_control_execution.py": 380,
    "operational_control_scope.py": 260,
    "operational_control_parsing.py": 260,
    "operational_control_serialization.py": 120,
    "tool_execution_outcomes.py": 360,
    "tool_execution_policy_support.py": 180,
    "tool_execution_resolution.py": 260,
    "tool_execution_persistence.py": 180,
    "optimizer_queries_support.py": 120,
    "optimizer_decisions_support.py": 340,
    "optimizer_presenters.py": 120,
}

REPOSITORY_EXTRACTION_TARGETS = {
    APP_DIR / "multi_agent_runtime.py": 0,
    APP_DIR / "optimizer_runtime.py": 0,
    APP_DIR / "proactive_reasoning_runtime.py": 0,
    APP_DIR / "integrations_runtime.py": 0,
    APP_DIR / "whatsapp_channel_runtime" / "implementation.py": 0,
    APP_DIR / "voice_channel_runtime.py": 0,
    APP_DIR / "growth_os_runtime.py": 0,
}

RUNTIME_DATA_ACCESS_PATTERN = re.compile(r"\b(?:fetch_one|fetch_all|execute)\(")


def test_application_service_facades_stay_small() -> None:
    application_dir = APP_DIR / "application"
    for filename, max_lines in APPLICATION_SERVICE_MAX_LINES.items():
        path = application_dir / filename
        assert path.exists(), filename
        assert _line_count(path) <= max_lines


def test_application_support_modules_stay_split_and_bounded() -> None:
    application_dir = APP_DIR / "application"
    for filename, max_lines in APPLICATION_SUPPORT_MAX_LINES.items():
        path = application_dir / filename
        assert path.exists(), filename
        assert _line_count(path) <= max_lines



def test_application_service_helper_modules_exist() -> None:
    expected = [
        APP_DIR / "application" / "operational_control_support.py",
        APP_DIR / "application" / "tool_execution_support.py",
        APP_DIR / "application" / "optimizer_support.py",
        APP_DIR / "application" / "integration_support.py",
        APP_DIR / "application" / "onboarding_support.py",
        APP_DIR / "application" / "outcomes_support.py",
        APP_DIR / "application" / "operational_control_execution.py",
        APP_DIR / "application" / "operational_control_scope.py",
        APP_DIR / "application" / "operational_control_parsing.py",
        APP_DIR / "application" / "operational_control_serialization.py",
        APP_DIR / "application" / "tool_execution_outcomes.py",
        APP_DIR / "application" / "tool_execution_policy_support.py",
        APP_DIR / "application" / "tool_execution_resolution.py",
        APP_DIR / "application" / "tool_execution_persistence.py",
        APP_DIR / "application" / "optimizer_queries_support.py",
        APP_DIR / "application" / "optimizer_decisions_support.py",
        APP_DIR / "application" / "optimizer_presenters.py",
        APP_DIR / "application" / "optimizer_constants.py",
        APP_DIR / "application" / "optimizer_handlers" / "commands.py",
        APP_DIR / "application" / "optimizer_handlers" / "queries.py",
        APP_DIR / "application" / "integration_handlers" / "commands.py",
        APP_DIR / "application" / "integration_handlers" / "queries.py",
        APP_DIR / "application" / "onboarding_handlers" / "commands.py",
        APP_DIR / "application" / "onboarding_handlers" / "queries.py",
    ]
    for path in expected:
        assert path.exists(), str(path.relative_to(ROOT_DIR))



def test_repository_extraction_targets_keep_runtime_sql_at_zero() -> None:
    for path, expected_count in REPOSITORY_EXTRACTION_TARGETS.items():
        content = path.read_text(encoding="utf-8")
        actual_count = len(RUNTIME_DATA_ACCESS_PATTERN.findall(content))
        assert actual_count <= expected_count, str(path.relative_to(ROOT_DIR))



def test_repository_modules_exist_for_runtime_data_access_boundaries() -> None:
    expected = [
        APP_DIR / "repositories" / "multi_agent.py",
        APP_DIR / "repositories" / "optimizer.py",
        APP_DIR / "repositories" / "proactive_reasoning.py",
        APP_DIR / "repositories" / "integrations_runtime.py",
        APP_DIR / "repositories" / "voice_channels.py",
        APP_DIR / "repositories" / "whatsapp_runtime.py",
        APP_DIR / "repositories" / "growth_os.py",
    ]
    for path in expected:
        assert path.exists(), str(path.relative_to(ROOT_DIR))


API_ROUTE_PATTERN = re.compile(r'@router\.(?:get|post|put|delete|patch)\((.*?)\)\s*\n(?:async\s+)?def\s+(\w+)', re.DOTALL)
ROUTE_PATH_PATTERN = re.compile(r"[\"\']([^\"\']+)[\"\']")
ALLOWED_NON_API_PREFIXES = {"/livez", "/healthz", "/readyz", "/public", "/webhooks"}
DOMAIN_DATA_ACCESS_TARGETS = {
    APP_DIR / "domains" / "bot_behavior.py": 0,
    APP_DIR / "domains" / "appointments.py": 0,
    APP_DIR / "domains" / "whatsapp_templates.py": 0,
    APP_DIR / "domains" / "whatsapp_flows.py": 0,
}


def test_api_router_contracts_are_explicit_and_prefixes_are_consistent() -> None:
    routers_dir = APP_DIR / "api" / "routers"
    missing_response_models: list[str] = []
    prefix_offenders: list[str] = []
    for path in sorted(routers_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        has_api_prefix_router = 'prefix="/api/v1' in text or "prefix='/api/v1" in text
        for args, func_name in API_ROUTE_PATTERN.findall(text):
            if "response_model=" not in args:
                missing_response_models.append(f"{path.relative_to(ROOT_DIR)}::{func_name}")
            path_match = ROUTE_PATH_PATTERN.search(args)
            if not path_match:
                continue
            route_path = path_match.group(1)
            allowed = route_path.startswith("/api/v1/") or any(route_path.startswith(prefix) for prefix in ALLOWED_NON_API_PREFIXES)
            if not allowed and not has_api_prefix_router:
                prefix_offenders.append(f"{path.relative_to(ROOT_DIR)}::{func_name}::{route_path}")
    assert missing_response_models == []
    assert prefix_offenders == []


def test_domain_data_access_keeps_moving_to_repositories() -> None:
    for path, max_count in DOMAIN_DATA_ACCESS_TARGETS.items():
        content = path.read_text(encoding="utf-8")
        actual_count = len(RUNTIME_DATA_ACCESS_PATTERN.findall(content))
        assert actual_count <= max_count, str(path.relative_to(ROOT_DIR))


def test_domain_repository_modules_exist_for_hybrid_boundaries() -> None:
    expected = [
        APP_DIR / "repositories" / "appointments_domain.py",
        APP_DIR / "repositories" / "bot_behavior_domain.py",
        APP_DIR / "repositories" / "whatsapp_flows_domain.py",
        APP_DIR / "repositories" / "whatsapp_templates_domain.py",
    ]
    for path in expected:
        assert path.exists(), str(path.relative_to(ROOT_DIR))


SELECTED_ROUTER_FLEXIBLE_MAX = {
    APP_DIR / "api" / "routers" / "appointments.py": 0,
    APP_DIR / "api" / "routers" / "growth_os.py": 0,
    APP_DIR / "api" / "routers" / "voice_channel.py": 0,
}


def test_selected_router_contracts_move_away_from_flexible_schema() -> None:
    for path, max_count in SELECTED_ROUTER_FLEXIBLE_MAX.items():
        content = path.read_text(encoding="utf-8")
        actual_count = content.count("FlexibleSchema")
        assert actual_count <= max_count, str(path.relative_to(ROOT_DIR))


def test_frontend_shell_files_stay_split_and_bounded() -> None:
    for path, max_lines in FRONTEND_COMPONENT_MAX_LINES.items():
        assert path.exists(), str(path)
        assert _line_count(path) <= max_lines
    for path in FRONTEND_EXPECTED_SPLITS:
        assert path.exists(), str(path)
    assert _line_count(FRONTEND_DIR / "features" / "bot-studio" / "flow" / "BotStudioFlowBody.tsx") <= 120
    assert _line_count(FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowController.ts") <= 140
    assert _line_count(FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowActions.ts") <= 120
    assert _line_count(FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioCreateFlowActions.ts") <= 160
    assert _line_count(FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioReconfigureFlowActions.ts") <= 120
    assert _line_count(FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowActionHelpers.ts") <= 180
    assert _line_count(FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowNavigation.ts") <= 140
    assert _line_count(FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowStateModel.ts") <= 220
    assert _line_count(FRONTEND_DIR / "features" / "bot-studio" / "flow" / "useBotStudioFlowTelemetry.ts") <= 80


def test_frontend_session_helpers_share_contracts_across_server_and_edge() -> None:
    shared = (FRONTEND_DIR / "app" / "lib" / "auth" / "shared-session.ts").read_text(encoding="utf-8")
    server = (FRONTEND_DIR / "app" / "lib" / "session.ts").read_text(encoding="utf-8")
    edge = (FRONTEND_DIR / "app" / "lib" / "auth" / "edge-session.ts").read_text(encoding="utf-8")
    refresh = (FRONTEND_DIR / "app" / "lib" / "auth" / "refresh.ts").read_text(encoding="utf-8")
    assert "AUTH_ME_PATH" in shared
    assert "AUTH_REFRESH_PATH" in shared
    assert "resolveSessionOrganizationId" in shared
    assert "fetchSessionUserFromApi" in shared
    assert 'from "./auth/shared-session"' in server
    assert 'from "./shared-session.ts"' in edge
    assert "AUTH_REFRESH_PATH" in refresh
