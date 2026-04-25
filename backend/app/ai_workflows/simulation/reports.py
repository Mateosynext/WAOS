from __future__ import annotations
def build_simulation_report(results: list[dict]) -> dict:
    total=len(results); failed=[r for r in results if not r.get("passed")]; blocking=[i for r in failed for i in r.get("issues",[])]
    return {"total":total,"passed":total-len(failed),"failed":len(failed),"average_score":sum(float(r.get("score",0)) for r in results)/max(total,1),"blocking_failures":blocking,"risky_replies":[r for r in failed if r.get("reply")],"hallucination_risks":[i for i in blocking if "price" in i],"handoff_failures":[i for i in blocking if "handoff" in i],"tool_execution_risks":[i for i in blocking if "tool" in i],"go_live_recommendation":"blocked" if blocking else "ready_with_warnings"}
