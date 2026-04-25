from __future__ import annotations
from .scenario_builder import build_scenarios
from .judge import judge_scenario
from .reports import build_simulation_report
def run_simulation_suite(vertical_pack: dict, wizard: dict|None=None, count: int=8) -> dict:
    scenarios=build_scenarios(vertical_pack,count); results=[judge_scenario(s) for s in scenarios]; report=build_simulation_report(results); report["scenarios"]=results; return report
