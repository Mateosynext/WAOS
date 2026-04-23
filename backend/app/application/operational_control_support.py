from __future__ import annotations

from .operational_control_execution import OperationalControlExecutionMixin
from .operational_control_parsing import OperationalControlParsingMixin
from .operational_control_scope import OperationalControlScopeMixin
from .operational_control_serialization import OperationalControlSerializationMixin


class OperationalControlSupportMixin(
    OperationalControlExecutionMixin,
    OperationalControlScopeMixin,
    OperationalControlParsingMixin,
    OperationalControlSerializationMixin,
):
    pass
