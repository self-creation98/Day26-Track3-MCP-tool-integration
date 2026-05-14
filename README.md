# Lab Submission: Database MCP Server with FastMCP and SQLite

This repository is my completed submission for the lab **Build a Database MCP Server with FastMCP and SQLite**.

The project implements a local MCP server that exposes a small SQLite database through three tools:

- `search`
- `insert`
- `aggregate`

It also exposes database schema context through MCP resources, validates unsafe requests before SQL execution, includes automated tests, and provides screenshots from MCP Inspector and Codex MCP configuration.

Docker is not required. The database runs as a local SQLite file.

## Submission Checklist

| Requirement | Status | Evidence |
|---|---:|---|
| FastMCP server starts | Done | `implementation/mcp_server.py`, `screenshots/MCP_Connected.png` |
| SQLite database with seed data | Done | `implementation/init_db.py`, `implementation/sqlite_lab.db` |
| `search` tool | Done | `screenshots/MCP_Search_tools.png` |
| `insert` tool | Done | `screenshots/MCP_Insert_Tools.png` |
| `aggregate` tool | Done | `screenshots/MCP_Aggregate_Tools.png` |
| Full schema resource | Done | `screenshots/MCP_Resources.png` |
| Per-table schema template | Done | `screenshots/MCP_Resources_template.png` |
| Validation and clear errors | Done | `screenshots/MCP_Error.png` |
| Repeatable verification | Done | `implementation/verify_server.py`, `screenshots/MCP_verify.png` |
| MCP client configuration | Done | `screenshots/MCP_LIST.png` |

## Project Structure

```text
.
|-- implementation/
|   |-- __init__.py
|   |-- db.py
|   |-- init_db.py
|   |-- mcp_server.py
|   |-- sqlite_lab.db
|   |-- start_inspector.ps1
|   |-- start_inspector.sh
|   |-- verify_server.py
|   `-- tests/
|       |-- test_db.py
|       `-- test_server.py
|-- pseudocode/
|-- screenshots/
|-- README.md
|-- Rubric.md
|-- Tips.md
|-- requirements.txt
|-- pyproject.toml
`-- .gitignore
```

## Database Model

The SQLite database contains three related tables:

- `students`: student records with `name`, `cohort`, and `email`
- `courses`: course records with `code`, `title`, and `credits`
- `enrollments`: many-to-many enrollment records with `score` and `status`

The database can be recreated at any time with:

```bash
python implementation/init_db.py
```

## Setup Instructions

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Optional virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Optional virtual environment on macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Initialize the database:

```bash
python implementation/init_db.py
```

Start the MCP server over stdio:

```bash
python implementation/mcp_server.py
```

## MCP Tools

### `search`

Searches a validated table with optional filters, selected columns, ordering, limit, and offset.

Example:

```json
{
  "table": "students",
  "filters": {
    "cohort": "A1"
  },
  "columns": ["id", "name", "cohort"],
  "limit": 20,
  "offset": 0,
  "order_by": "name",
  "descending": false
}
```

Supported filter operators:

```text
=, ==, eq, !=, <>, ne, >, gt, >=, gte, <, lt, <=, lte, like, in
```

### `insert`

Inserts one row into a known table after validating that all supplied columns exist.

Example:

```json
{
  "table": "students",
  "values": {
    "name": "Demo Student",
    "cohort": "A1",
    "email": "demo.student@example.edu"
  }
}
```

### `aggregate`

Runs `count`, `avg`, `sum`, `min`, or `max` with optional filters and grouping.

Example:

```json
{
  "table": "enrollments",
  "metric": "avg",
  "column": "score",
  "group_by": "status"
}
```

## MCP Resources

The server exposes:

```text
schema://database
schema://table/{table_name}
```

Examples:

```text
schema://database
schema://table/students
schema://table/courses
schema://table/enrollments
```

## Validation and Safety

The database layer is implemented in `implementation/db.py`. It rejects invalid requests before running SQL.

Rejected cases include:

- unknown table names
- unknown column names
- unsupported filter operators
- unsupported aggregate metrics
- aggregate calls missing required columns
- `avg` or `sum` on non-numeric columns
- empty inserts
- invalid limit or offset values
- database constraint violations during insert

SQL values are passed as bound parameters. Table names and column names are only used after being validated against the live SQLite schema.

## Testing and Verification

Run automated tests:

```bash
python -m pytest -q
```

Latest result:

```text
15 passed
```

Run the repeatable MCP verification script:

```bash
python implementation/verify_server.py
```

Expected output:

```text
Tools discovered: aggregate, insert, search
Resources discovered: schema://database
Resource templates discovered: schema://table/{table_name}
Search cohort A1 count: 2
Invalid request returned a clear error: Error executing tool search: Unknown table 'missing_table'. Known tables: courses, enrollments, students.
Verification completed successfully.
```

## MCP Inspector Demo

Windows:

```powershell
.\implementation\start_inspector.ps1
```

macOS/Linux:

```bash
chmod +x implementation/start_inspector.sh
./implementation/start_inspector.sh
```

Manual command:

```bash
npx -y @modelcontextprotocol/inspector python /ABSOLUTE/PATH/TO/implementation/mcp_server.py
```

In MCP Inspector, the server was verified with:

- tool discovery for `search`, `insert`, and `aggregate`
- successful `search` call for students in cohort `A1`
- successful `insert` call for a demo student
- successful `aggregate` call for average enrollment score by status
- successful read of `schema://database`
- successful read of `schema://table/students`
- invalid `search` call for `missing_table`, returning a clear validation error

## Codex MCP Client Configuration

This project was also configured as a Codex MCP server named `sqlite_lab`.

Example Codex config:

```toml
[mcp_servers.sqlite_lab]
command = "/ABSOLUTE/PATH/TO/python"
args = ["/ABSOLUTE/PATH/TO/implementation/mcp_server.py"]
```

Verified local Windows config:

```toml
[mcp_servers.sqlite_lab]
command = 'C:\Python314\python.exe'
args = ['C:\Users\newch\Downloads\Day26-Track3-MCP-tool-integration\implementation\mcp_server.py']
```

Check the configured server:

```powershell
codex mcp list
```

If `codex` is not in `PATH`, use the full Codex executable path:

```powershell
& "C:\Users\newch\AppData\Local\OpenAI\Codex\bin\codex.exe" mcp list
```

## Screenshot Evidence

The following screenshots are included in the `screenshots/` folder:

```text
screenshots/MCP_LIST.png
screenshots/MCP_verify.png
screenshots/MCP_Connected.png
screenshots/MCP_3 tools.png
screenshots/MCP_Search_tools.png
screenshots/MCP_Insert_Tools.png
screenshots/MCP_Aggregate_Tools.png
screenshots/MCP_Resources.png
screenshots/MCP_Resources_template.png
screenshots/MCP_Error.png
screenshots/MCP_Test.png
```

They demonstrate client configuration, server connection, tool discovery, successful tool calls, schema resources, dynamic resource templates, and validation errors.

## Suggested Two-Minute Demo Script

1. Run `python implementation/init_db.py`.
2. Run `python implementation/verify_server.py`.
3. Start MCP Inspector with `.\implementation\start_inspector.ps1`.
4. Show the connected SQLite Lab MCP Server.
5. Open Tools and show `search`, `insert`, and `aggregate`.
6. Run `search` on `students` with cohort `A1`.
7. Run `insert` to add a demo student.
8. Run `aggregate` to compute average `score` grouped by `status`.
9. Open Resources and read `schema://database`.
10. Open Resource Templates and read `schema://table/students`.
11. Run `search` with `missing_table` to show the clear validation error.

## Notes

The server first tries to import `FastMCP` from the standalone `fastmcp` package. It also supports the compatible import path from the official MCP Python SDK:

```python
from mcp.server.fastmcp import FastMCP
```

This keeps the lab easy to run in environments where the MCP SDK is already installed.
