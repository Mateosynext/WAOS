from __future__ import annotations
import importlib, json
MODULES=["eval_wizard_generation","eval_autofix_safety","eval_runtime_reply_safety","eval_simulation_judge","eval_vertical_detection","eval_agent_policy_pack","eval_whatsapp_template_pack","eval_go_live_readiness"]
def main():
    results=[]; failed=False
    for name in MODULES:
        result=importlib.import_module(f"backend.app.ai_evals.{name}").run_eval(); results.append(result); failed = failed or bool(result.get("failures"))
    print(json.dumps({"score":sum(r["score"] for r in results)/len(results),"results":results},ensure_ascii=False,indent=2))
    if failed: raise SystemExit(1)
if __name__=="__main__": main()
