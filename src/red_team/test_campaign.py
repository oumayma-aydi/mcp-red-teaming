import asyncio
import json
import os
import time
from pathlib import Path

import yaml

from src.agent.prompts import PROMPTS
from src.red_team.attack_runner import run_scenario
from src.red_team.scenario_loader import load_scenarios


async def run_campaign(config_path: str) -> None:
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    model = os.getenv("MODEL")
    scenarios = load_scenarios(cfg["scenarios_dir"])
    run_id = f"{cfg['profile']}-{int(time.time())}"
    print(f"Campagne {run_id} | modèle {model} | {len(scenarios)} scénarios")

    records = []
    for sc in scenarios:
        rec = await run_scenario(sc, model, PROMPTS[cfg["system_prompt"]], run_id, cfg.get("max_turns", 5))
        records.append(rec)
        print(f"  {sc.scenario_id:6} {rec['verdict']:13} {rec['duration_s']}s")
        await asyncio.sleep(cfg.get("delay_s", 1))  # évite le rate limit

    counted = [r for r in records if r["verdict"] in ("PASS", "FAIL")]
    fails = sum(r["verdict"] == "FAIL" for r in counted)
    asr = round(100 * fails / len(counted), 1) if counted else None
    print(f"ASR provisoire : {asr}% ({fails}/{len(counted)}, ERROR/INCONCLUSIVE exclus)")

    out = Path(cfg["output"])
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Résultats : {out}")