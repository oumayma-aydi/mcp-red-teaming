import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]


class MCPClient:
    """Lance le serveur MCP en sous-processus (stdio) et expose list_tools / call_tool."""

    def __init__(self, server_module: str = "src.mcp_environment.server", env: dict | None = None):
        self.server_module = server_module
        self.env = env or {}
        self._stack = AsyncExitStack()
        self.session: ClientSession | None = None

    async def __aenter__(self):
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", self.server_module],
            cwd=str(ROOT),
            env=self.env,
        )
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc):
        await self._stack.aclose()

    async def list_tools(self):
        res = await self.session.list_tools()
        return res.tools

    async def call_tool(self, name: str, arguments: dict) -> tuple[str, bool]:
        res = await self.session.call_tool(name, arguments)
        text = "\n".join(c.text for c in res.content if getattr(c, "type", "") == "text")
        return text, bool(res.isError)