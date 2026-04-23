from __future__ import annotations

from .tool_execution_outcomes import ToolExecutionOutcomesMixin
from .tool_execution_persistence import ToolExecutionPersistenceMixin
from .tool_execution_policy_support import ToolExecutionPolicySupportMixin
from .tool_execution_resolution import ToolExecutionResolutionMixin


class ToolExecutionSupportMixin(
    ToolExecutionOutcomesMixin,
    ToolExecutionPolicySupportMixin,
    ToolExecutionResolutionMixin,
    ToolExecutionPersistenceMixin,
):
    pass
