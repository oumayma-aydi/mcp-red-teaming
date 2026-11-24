import argparse
import asyncio
import json
import os

from dotenv import load_dotenv

from src.agent.llm_agent import LLMAgent
from src.agent.prompts import BASELINE_SYSTEM_PROMPT
from src.mcp_environment.client import MCPClient
from src.red_team.test_campaign import run_campaign


async def smoke_test(prompt: str) -> None:
    model = os.getenv("MODEL", "openai/gpt-oss-120b")
    async with MCPClient() as mcp:
        agent = LLMAgent(mcp, model, BASELINE_SYSTEM_PROMPT)
        result = await agent.run(prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="Find the support procedure for password reset.")
    parser.add_argument("--config", help="Lance une campagne complète (ex. configs/baseline.yaml)")
    args = parser.parse_args()
    if args.config:
        asyncio.run(run_campaign(args.config))
    else:
        asyncio.run(smoke_test(args.prompt))