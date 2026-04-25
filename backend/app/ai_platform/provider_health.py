from __future__ import annotations
from dataclasses import dataclass
@dataclass
class ProviderHealth:
    provider: str; model: str; status: str="available"; timeout_rate: float=0; error_rate: float=0; circuit_breaker_open: bool=False; fallback_available: bool=True
def snapshot(provider: str, model: str) -> dict:
    return ProviderHealth(provider=provider, model=model).__dict__
