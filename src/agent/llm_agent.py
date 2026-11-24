import json
import time

from groq import AsyncGroq

from src.mcp_environment.client import MCPClient


class LLMAgent:
    def __init__(self, mcp: MCPClient, model: str, system_prompt: str,
                 max_turns: int = 5, temperature: float = 0.0,
                 seed: int | None = 42, max_tokens: int = 4000):
        self.mcp = mcp
        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens
        self.llm = AsyncGroq(max_retries=2)

    async def run(self, user_message: str) -> dict:
        start = time.time()
        mcp_tools = await self.mcp.list_tools()
        tools = [
            {"type": "function",
             "function": {"name": t.name, "description": t.description or "",
                          "parameters": t.inputSchema}}
            for t in mcp_tools
        ]
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        tool_calls = []
        malformed = 0

        for _ in range(self.max_turns):
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=self.temperature,
                seed=self.seed,
                max_completion_tokens=self.max_tokens,
            )
            choice = response.choices[0]
            msg = choice.message
            messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                if choice.finish_reason == "length" or not (msg.content or "").strip():
                    return self._result("truncated", msg.content, tool_calls, start, malformed)
                return self._result("completed", msg.content, tool_calls, start, malformed)

            for call in msg.tool_calls:
                name = call.function.name
                arguments: dict = {}          # réinitialisé à chaque appel
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                    if not isinstance(arguments, dict):
                        raise ValueError("arguments must be a JSON object")
                    output, is_error = await self.mcp.call_tool(name, arguments)
                except (json.JSONDecodeError, ValueError) as exc:
                    output, is_error = f"Invalid tool arguments: {exc}", True
                    malformed += 1

                tool_calls.append({"tool": name, "args": arguments,
                                   "output": output, "is_error": is_error})
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "name": name, "content": output})

        return self._result("max_turns_reached", None, tool_calls, start, malformed)

    def _result(self, status, final, tool_calls, start, malformed=0):
        return {
            "status": status,
            "final_response": final,
            "tool_calls": tool_calls,
            "malformed_tool_calls": malformed,
            "duration_s": round(time.time() - start, 2),
        }