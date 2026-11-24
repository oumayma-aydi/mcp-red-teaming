
import json
import time

from groq import AsyncGroq

from src.mcp_environment.client import MCPClient


class LLMAgent:
    def __init__(
        self,
        mcp: MCPClient,
        model: str,
        system_prompt: str,
        max_turns: int = 5
    ):
        self.mcp = mcp
        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns

        # Client asynchrone Groq
        self.llm = AsyncGroq()

    async def run(self, user_message: str) -> dict:
        start = time.time()

        # 1. Récupérer les outils disponibles depuis MCP
        mcp_tools = await self.mcp.list_tools()

        # 2. Convertir les outils MCP au format Groq
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema
                }
            }
            for tool in mcp_tools
        ]

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        tool_calls = []

        # 3. Boucle de tool calling
        for _ in range(self.max_turns):

            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1000
            )

            assistant_message = response.choices[0].message

            # Ajouter la réponse de l'assistant à l'historique
            messages.append(
                assistant_message.model_dump(exclude_none=True)
            )

            # 4. Si aucun outil n'est demandé, retourner la réponse
            if not assistant_message.tool_calls:
                return self._result(
                    "completed",
                    assistant_message.content,
                    tool_calls,
                    start
                )

            # 5. Exécuter les outils demandés par Groq
            for call in assistant_message.tool_calls:

                tool_name = call.function.name

                try:
                    arguments = json.loads(call.function.arguments or "{}")

                    output, is_error = await self.mcp.call_tool(
                        tool_name,
                        arguments
                    )

                except (json.JSONDecodeError, ValueError) as exc:
                    output = f"Invalid tool arguments: {exc}"
                    is_error = True

                tool_calls.append({
                    "tool": tool_name,
                    "args": arguments if "arguments" in locals() else {},
                    "output": output,
                    "is_error": is_error
                })

                # 6. Retourner le résultat MCP à Groq
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": tool_name,
                    "content": output
                })

        return self._result(
            "max_turns_reached",
            None,
            tool_calls,
            start
        )

    def _result(self, status, final, tool_calls, start):
        return {
            "status": status,
            "final_response": final,
            "tool_calls": tool_calls,
            "duration_s": round(time.time() - start, 2)
        }
