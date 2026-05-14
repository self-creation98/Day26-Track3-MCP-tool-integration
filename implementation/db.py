from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

try:
    from .init_db import DEFAULT_DB_PATH
except ImportError:  # pragma: no cover - supports running files directly
    from init_db import DEFAULT_DB_PATH


class ValidationError(ValueError):
    """Raised when a request cannot be safely executed."""


class SQLiteAdapter:
    """Small validated database adapter used by the MCP tools."""

    SUPPORTED_OPERATORS = {
        "=": "=",
        "==": "=",
        "eq": "=",
        "!=": "!=",
        "<>": "!=",
        "ne": "!=",
        ">": ">",
        "gt": ">",
        ">=": ">=",
        "gte": ">=",
        "<": "<",
        "lt": "<",
        "<=": "<=",
        "lte": "<=",
        "like": "LIKE",
        "in": "IN",
    }
    AGGREGATES = {"count", "avg", "sum", "min", "max"}

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def list_tables(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> dict[str, Any]:
        table_name = self._validate_table(table)
        quoted_table = self._quote_identifier(table_name)

        with self.connect() as connection:
            columns = connection.execute(f"PRAGMA table_info({quoted_table})").fetchall()
            foreign_keys = connection.execute(f"PRAGMA foreign_key_list({quoted_table})").fetchall()

        return {
            "table": table_name,
            "columns": [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "primary_key": bool(row["pk"]),
                }
                for row in columns
            ],
            "foreign_keys": [
                {
                    "column": row["from"],
                    "references_table": row["table"],
                    "references_column": row["to"],
                    "on_update": row["on_update"],
                    "on_delete": row["on_delete"],
                }
                for row in foreign_keys
            ],
        }

    def get_database_schema(self) -> dict[str, Any]:
        return {
            "database": str(self.db_path),
            "tables": {table: self.get_table_schema(table) for table in self.list_tables()},
        }

    def search(
        self,
        table: str,
        filters: list[dict[str, Any]] | dict[str, Any] | None = None,
        columns: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        table_name = self._validate_table(table)
        selected_columns = self._validate_columns(table_name, columns) if columns else self._table_columns(table_name)
        limit_value = self._validate_limit(limit)
        offset_value = self._validate_offset(offset)
        where_sql, params = self._build_where_clause(table_name, filters)

        order_sql = ""
        if order_by:
            order_column = self._validate_column(table_name, order_by)
            direction = "DESC" if descending else "ASC"
            order_sql = f" ORDER BY {self._quote_identifier(order_column)} {direction}"

        sql = (
            f"SELECT {', '.join(self._quote_identifier(column) for column in selected_columns)} "
            f"FROM {self._quote_identifier(table_name)}"
            f"{where_sql}{order_sql} LIMIT ? OFFSET ?"
        )

        with self.connect() as connection:
            rows = connection.execute(sql, [*params, limit_value, offset_value]).fetchall()

        return {
            "table": table_name,
            "columns": selected_columns,
            "count": len(rows),
            "limit": limit_value,
            "offset": offset_value,
            "rows": [dict(row) for row in rows],
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        table_name = self._validate_table(table)
        if not isinstance(values, dict) or not values:
            raise ValidationError("Insert values must be a non-empty object.")

        columns = self._validate_columns(table_name, list(values.keys()))
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(self._quote_identifier(column) for column in columns)

        sql = f"INSERT INTO {self._quote_identifier(table_name)} ({column_sql}) VALUES ({placeholders})"
        params = [values[column] for column in columns]

        with self.connect() as connection:
            try:
                cursor = connection.execute(sql, params)
                inserted_id = cursor.lastrowid
                connection.commit()
            except sqlite3.IntegrityError as exc:
                raise ValidationError(f"Insert failed because a database constraint was violated: {exc}.") from exc

        inserted = dict(values)
        if "id" in self._table_columns(table_name) and "id" not in inserted:
            inserted["id"] = inserted_id

        return {"table": table_name, "inserted": inserted}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | dict[str, Any] | None = None,
        group_by: str | list[str] | None = None,
    ) -> dict[str, Any]:
        table_name = self._validate_table(table)
        metric_name = self._validate_metric(metric)
        group_columns = self._validate_group_by(table_name, group_by)
        where_sql, params = self._build_where_clause(table_name, filters)

        if metric_name == "count" and column is None:
            metric_sql = "COUNT(*)"
        else:
            if column is None:
                raise ValidationError(f"Aggregate '{metric_name}' requires a column.")
            column_name = self._validate_column(table_name, column)
            if metric_name in {"avg", "sum"}:
                self._validate_numeric_column(table_name, column_name, metric_name)
            metric_sql = f"{metric_name.upper()}({self._quote_identifier(column_name)})"

        select_parts = [self._quote_identifier(column_name) for column_name in group_columns]
        select_parts.append(f"{metric_sql} AS value")
        group_sql = ""
        if group_columns:
            group_sql = " GROUP BY " + ", ".join(self._quote_identifier(column_name) for column_name in group_columns)

        sql = (
            f"SELECT {', '.join(select_parts)} "
            f"FROM {self._quote_identifier(table_name)}"
            f"{where_sql}{group_sql}"
        )

        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        return {
            "table": table_name,
            "metric": metric_name,
            "column": column,
            "group_by": group_columns,
            "rows": [dict(row) for row in rows],
        }

    def _validate_table(self, table: str) -> str:
        if not isinstance(table, str) or not table.strip():
            raise ValidationError("Table name must be a non-empty string.")

        table_name = table.strip()
        tables = self.list_tables()
        if table_name not in tables:
            raise ValidationError(f"Unknown table '{table_name}'. Known tables: {', '.join(tables)}.")
        return table_name

    def _validate_column(self, table: str, column: str) -> str:
        if not isinstance(column, str) or not column.strip():
            raise ValidationError("Column name must be a non-empty string.")

        column_name = column.strip()
        columns = self._table_columns(table)
        if column_name not in columns:
            raise ValidationError(
                f"Unknown column '{column_name}' for table '{table}'. Known columns: {', '.join(columns)}."
            )
        return column_name

    def _validate_columns(self, table: str, columns: list[str]) -> list[str]:
        if not isinstance(columns, list) or not columns:
            raise ValidationError("Columns must be a non-empty list of column names.")
        return [self._validate_column(table, column) for column in columns]

    def _validate_metric(self, metric: str) -> str:
        if not isinstance(metric, str):
            raise ValidationError("Aggregate metric must be a string.")
        metric_name = metric.strip().lower()
        if metric_name not in self.AGGREGATES:
            raise ValidationError(
                f"Unsupported aggregate metric '{metric}'. Supported metrics: {', '.join(sorted(self.AGGREGATES))}."
            )
        return metric_name

    def _validate_numeric_column(self, table: str, column: str, metric: str) -> None:
        column_type = self._column_type(table, column).upper()
        numeric_markers = ("INT", "REAL", "NUM", "DEC", "DOUB", "FLOA")
        if not any(marker in column_type for marker in numeric_markers):
            raise ValidationError(
                f"Aggregate '{metric}' requires a numeric column; '{column}' has type '{column_type}'."
            )

    def _validate_group_by(self, table: str, group_by: str | list[str] | None) -> list[str]:
        if group_by is None:
            return []
        if isinstance(group_by, str):
            return [self._validate_column(table, group_by)]
        if isinstance(group_by, list) and group_by:
            return [self._validate_column(table, column) for column in group_by]
        raise ValidationError("group_by must be a column name or a non-empty list of column names.")

    def _build_where_clause(
        self,
        table: str,
        filters: list[dict[str, Any]] | dict[str, Any] | None,
    ) -> tuple[str, list[Any]]:
        normalized_filters = self._normalize_filters(filters)
        if not normalized_filters:
            return "", []

        clauses: list[str] = []
        params: list[Any] = []
        for filter_item in normalized_filters:
            column = self._validate_column(table, filter_item["column"])
            operator = self._validate_operator(filter_item["operator"])
            value = filter_item.get("value")

            if operator == "IN":
                if not isinstance(value, (list, tuple)) or len(value) == 0:
                    raise ValidationError("The 'in' operator requires a non-empty list of values.")
                placeholders = ", ".join("?" for _ in value)
                clauses.append(f"{self._quote_identifier(column)} IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{self._quote_identifier(column)} {operator} ?")
                params.append(value)

        return " WHERE " + " AND ".join(clauses), params

    def _normalize_filters(self, filters: list[dict[str, Any]] | dict[str, Any] | None) -> list[dict[str, Any]]:
        if filters is None:
            return []

        if isinstance(filters, dict):
            if {"column", "operator"}.issubset(filters):
                return [filters]
            return [{"column": column, "operator": "=", "value": value} for column, value in filters.items()]

        if isinstance(filters, list):
            normalized = []
            for filter_item in filters:
                if not isinstance(filter_item, dict):
                    raise ValidationError("Each filter must be an object.")
                if "column" not in filter_item or "operator" not in filter_item:
                    raise ValidationError("Each filter must include 'column' and 'operator'.")
                normalized.append(filter_item)
            return normalized

        raise ValidationError("Filters must be an object, a list of objects, or null.")

    def _validate_operator(self, operator: str) -> str:
        if not isinstance(operator, str):
            raise ValidationError("Filter operator must be a string.")
        operator_key = operator.strip().lower()
        if operator_key not in self.SUPPORTED_OPERATORS:
            raise ValidationError(
                f"Unsupported filter operator '{operator}'. Supported operators: "
                f"{', '.join(sorted(self.SUPPORTED_OPERATORS))}."
            )
        return self.SUPPORTED_OPERATORS[operator_key]

    def _validate_limit(self, limit: int) -> int:
        try:
            limit_value = int(limit)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Limit must be an integer.") from exc
        if limit_value < 1 or limit_value > 100:
            raise ValidationError("Limit must be between 1 and 100.")
        return limit_value

    def _validate_offset(self, offset: int) -> int:
        try:
            offset_value = int(offset)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Offset must be an integer.") from exc
        if offset_value < 0:
            raise ValidationError("Offset must be greater than or equal to 0.")
        return offset_value

    def _table_columns(self, table: str) -> list[str]:
        schema = self.get_table_schema(table)
        return [column["name"] for column in schema["columns"]]

    def _column_type(self, table: str, column: str) -> str:
        schema = self.get_table_schema(table)
        for schema_column in schema["columns"]:
            if schema_column["name"] == column:
                return schema_column["type"]
        raise ValidationError(f"Unknown column '{column}' for table '{table}'.")

    def _quote_identifier(self, identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'
