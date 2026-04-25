from __future__ import annotations

from dataclasses import dataclass, field

LIMITS = {"conservative": 0.50, "balanced": 2.0, "aggressive": 5.0, "savage": 12.0, "godmode": 25.0}
SIM_LIMITS = {"conservative": 3, "balanced": 8, "aggressive": 15, "savage": 25, "godmode": 50}


class CostLimitExceeded(RuntimeError):
    pass


@dataclass
class CostGovernor:
    intensity: str = "balanced"
    max_cost_usd: float | None = None
    spent: float = 0.0
    charges: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        default = LIMITS.get(self.intensity, LIMITS["balanced"])
        self.max_cost_usd = float(self.max_cost_usd if self.max_cost_usd is not None else default)
        if self.max_cost_usd < 0:
            raise ValueError("max_cost_usd must be non-negative")

    @property
    def max_simulations(self) -> int:
        return SIM_LIMITS.get(self.intensity, SIM_LIMITS["balanced"])

    def charge(self, operation: str, estimated_cost_usd: float) -> dict:
        amount = max(0.0, float(estimated_cost_usd or 0.0))
        next_total = self.spent + amount
        if next_total > float(self.max_cost_usd or 0):
            raise CostLimitExceeded(f"AI cost limit exceeded before {operation}: {next_total:.4f}>{float(self.max_cost_usd or 0):.4f}")
        self.spent = next_total
        item = {"operation": operation, "estimated_cost_usd": amount, "running_total_usd": self.spent, "max_cost_usd": self.max_cost_usd}
        self.charges.append(item)
        return item
