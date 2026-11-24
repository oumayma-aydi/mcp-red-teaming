import time

from src.agent.llm_agent import LLMAgent
from src.evaluation.evaluator import evaluate
from src.mcp_environment.client import MCPClient
from src.red_team.scenario_loader import Scenario


async def run_scenario(scenario: Scenario, model: str, system_prompt: str,
                       run_id: str, max_turns: int = 5) -> dict:
    record = {
        "run_id": run_id,
        "scenario_id": scenario.scenario_id,
        "category": scenario.category,
        "severity": scenario.severity,
        "input": scenario.input,
    }
    start = time.time()
    try:
        env = {"RUN_ID": run_id, "SCENARIO_ID": scenario.scenario_id}
        async with MCPClient(env=env) as mcp:
            agent = LLMAgent(mcp, model, system_prompt, max_turns=max_turns)
            result = await agent.run(scenario.input)
        record.update(result)
        record.update(evaluate(scenario, result))
    except Exception as e:  # erreur technique : PAS une attaque bloquée
        record.update({"status": "error", "final_response": None, "tool_calls": [],
                       "verdict": "ERROR", "matched_rules": [], "error": repr(e),
                       "duration_s": round(time.time() - start, 2)})
    return record