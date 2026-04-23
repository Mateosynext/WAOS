from __future__ import annotations

from .optimizer_decisions_support import OptimizerDecisionsSupportMixin
from .optimizer_presenters import OptimizerPresentersMixin
from .optimizer_queries_support import OptimizerQueriesSupportMixin


class OptimizerSupportMixin(
    OptimizerQueriesSupportMixin,
    OptimizerDecisionsSupportMixin,
    OptimizerPresentersMixin,
):
    pass
