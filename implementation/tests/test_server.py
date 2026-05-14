from __future__ import annotations

import json
import asyncio

import pytest

from implementation.init_db import create_database
from implementation.mcp_server import DB_PATH, mcp


def _text_payload(result):
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, list) and result:
        return getattr(result[0], "text", getattr(result[0], "content", str(result[0])))
    return getattr(result, "content", str(result))


def _json_payload(result):
    if isinstance(result, tuple) and len(result) > 1 and isinstance(result[1], dict):
        return result[1]
    return json.loads(_text_payload(result))


@pytest.fixture(autouse=True)
def fresh_database():
    create_database(DB_PATH)


def test_tools_and_resources_are_discoverable():
    async def run_test():
        tools = await mcp.list_tools()
        resources = await mcp.list_resources()
        templates = await mcp.list_resource_templates()

        assert sorted(tool.name for tool in tools) == ["aggregate", "insert", "search"]
        assert "schema://database" in {str(resource.uri) for resource in resources}
        assert "schema://table/{table_name}" in {template.uriTemplate for template in templates}

    asyncio.run(run_test())


def test_valid_tool_calls_and_resources():
    async def run_test():
        search_result = _json_payload(
            await mcp.call_tool("search", {"table": "students", "filters": {"cohort": "A1"}, "order_by": "name"})
        )
        insert_result = _json_payload(
            await mcp.call_tool(
                "insert",
                {
                    "table": "students",
                    "values": {"name": "Lan Vo", "cohort": "A1", "email": "lan.vo@example.edu"},
                },
            )
        )
        aggregate_result = _json_payload(
            await mcp.call_tool("aggregate", {"table": "enrollments", "metric": "avg", "column": "score"})
        )
        schema_result = _json_payload(await mcp.read_resource("schema://table/students"))

        assert search_result["count"] == 2
        assert insert_result["inserted"]["id"] > 0
        assert aggregate_result["rows"][0]["value"] > 0
        assert schema_result["table"] == "students"

    asyncio.run(run_test())


def test_invalid_tool_call_returns_error():
    async def run_test():
        with pytest.raises(Exception, match="Unknown table"):
            await mcp.call_tool("search", {"table": "missing_table"})

    asyncio.run(run_test())
