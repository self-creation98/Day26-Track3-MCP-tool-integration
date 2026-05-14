from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from fastmcp import FastMCP
except ImportError:  # The official MCP SDK also ships a compatible FastMCP server.
    from mcp.server.fastmcp import FastMCP

try:
    from .db import SQLiteAdapter
    from .init_db import DEFAULT_DB_PATH, create_database
except ImportError:  # pragma: no cover - supports running this file directly
    from db import SQLiteAdapter
    from init_db import DEFAULT_DB_PATH, create_database


def _database_path() -> Path:
    return Path(os.environ.get("SQLITE_LAB_DB_PATH", DEFAULT_DB_PATH)).resolve()


DB_PATH = _database_path()
if not DB_PATH.exists():
    create_database(DB_PATH)

adapter = SQLiteAdapter(DB_PATH)
mcp = FastMCP("SQLite Lab MCP Server")


@mcp.tool(name="search")
def search(
    table: str,
    filters: list[dict[str, Any]] | dict[str, Any] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search a table with validated filters, selected columns, ordering, and pagination."""
    return adapter.search(
        table=table,
        filters=filters,
        columns=columns,
        limit=limit,
        offset=offset,
        order_by=order_by,
        descending=descending,
    )


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert one row into a known table after validating all supplied columns."""
    return adapter.insert(table=table, values=values)


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict[str, Any]] | dict[str, Any] | None = None,
    group_by: str | list[str] | None = None,
) -> dict[str, Any]:
    """Run count, avg, sum, min, or max over a validated table and optional group."""
    return adapter.aggregate(table=table, metric=metric, column=column, filters=filters, group_by=group_by)


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return a JSON snapshot of every exposed table, column, and foreign key."""
    return json.dumps(adapter.get_database_schema(), indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return a JSON schema description for a single validated table."""
    return json.dumps(adapter.get_table_schema(table_name), indent=2)


if __name__ == "__main__":
    mcp.run()
