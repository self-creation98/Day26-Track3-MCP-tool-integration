from __future__ import annotations

import asyncio
import json
from typing import Any

try:
    from .init_db import create_database
    from .mcp_server import DB_PATH, mcp
except ImportError:  # pragma: no cover - supports running this file directly
    from init_db import create_database
    from mcp_server import DB_PATH, mcp


def _text_payload(result: Any) -> str:
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, list) and result:
        return getattr(result[0], "text", getattr(result[0], "content", str(result[0])))
    if isinstance(result, list):
        return ""
    return getattr(result, "content", str(result))


def _json_payload(result: Any) -> dict[str, Any]:
    if isinstance(result, tuple) and len(result) > 1 and isinstance(result[1], dict):
        return result[1]
    return json.loads(_text_payload(result))


async def main() -> None:
    create_database(DB_PATH)

    tools = await mcp.list_tools()
    tool_names = sorted(tool.name for tool in tools)
    print(f"Tools discovered: {', '.join(tool_names)}")
    assert tool_names == ["aggregate", "insert", "search"]

    resources = await mcp.list_resources()
    resource_uris = sorted(str(resource.uri) for resource in resources)
    print(f"Resources discovered: {', '.join(resource_uris)}")
    assert "schema://database" in resource_uris

    templates = await mcp.list_resource_templates()
    template_uris = sorted(template.uriTemplate for template in templates)
    print(f"Resource templates discovered: {', '.join(template_uris)}")
    assert "schema://table/{table_name}" in template_uris

    schema = await mcp.read_resource("schema://database")
    print(f"Database schema resource size: {len(_text_payload(schema))} characters")

    table_schema = await mcp.read_resource("schema://table/students")
    print(f"Students schema resource: {_json_payload(table_schema)['table']}")

    search_result = _json_payload(
        await mcp.call_tool(
            "search",
            {
                "table": "students",
                "filters": {"cohort": "A1"},
                "columns": ["id", "name", "cohort"],
                "order_by": "name",
            },
        )
    )
    print(f"Search cohort A1 count: {search_result['count']}")
    assert search_result["count"] >= 2

    insert_result = _json_payload(
        await mcp.call_tool(
            "insert",
            {
                "table": "students",
                "values": {
                    "name": "Lan Vo",
                    "cohort": "A1",
                    "email": "lan.vo@example.edu",
                },
            },
        )
    )
    print(f"Inserted student id: {insert_result['inserted']['id']}")

    aggregate_result = _json_payload(
        await mcp.call_tool(
            "aggregate",
            {"table": "enrollments", "metric": "avg", "column": "score", "group_by": "status"},
        )
    )
    print(f"Aggregate rows: {len(aggregate_result['rows'])}")
    assert aggregate_result["rows"]

    try:
        await mcp.call_tool("search", {"table": "missing_table"})
    except Exception as exc:
        print(f"Invalid request returned a clear error: {exc}")
    else:  # pragma: no cover - defensive guard for verification script
        raise AssertionError("Invalid search unexpectedly succeeded.")

    print("Verification completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
