from __future__ import annotations

import pytest

from implementation.db import SQLiteAdapter, ValidationError
from implementation.init_db import create_database


@pytest.fixture()
def adapter(tmp_path):
    db_path = tmp_path / "lab.db"
    create_database(db_path)
    return SQLiteAdapter(db_path)


def test_search_filters_ordering_and_pagination(adapter):
    result = adapter.search(
        "students",
        filters={"cohort": "A1"},
        columns=["id", "name", "cohort"],
        order_by="name",
        limit=1,
    )

    assert result["count"] == 1
    assert result["rows"][0]["cohort"] == "A1"
    assert set(result["rows"][0]) == {"id", "name", "cohort"}


def test_insert_returns_inserted_payload(adapter):
    result = adapter.insert(
        "students",
        {"name": "Lan Vo", "cohort": "A1", "email": "lan.vo@example.edu"},
    )

    assert result["table"] == "students"
    assert result["inserted"]["id"] > 0
    assert result["inserted"]["email"] == "lan.vo@example.edu"


def test_aggregate_count_and_average(adapter):
    count_result = adapter.aggregate("students", "count", group_by="cohort")
    avg_result = adapter.aggregate("enrollments", "avg", column="score", group_by="status")

    assert any(row["cohort"] == "A1" and row["value"] == 2 for row in count_result["rows"])
    assert avg_result["rows"]
    assert all("value" in row for row in avg_result["rows"])


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda db: db.search("missing_table"), "Unknown table"),
        (lambda db: db.search("students", columns=["missing_column"]), "Unknown column"),
        (
            lambda db: db.search("students", filters=[{"column": "cohort", "operator": "contains", "value": "A"}]),
            "Unsupported filter operator",
        ),
        (lambda db: db.insert("students", {}), "non-empty object"),
        (
            lambda db: db.insert("students", {"name": "Bad Duplicate", "cohort": "A1", "email": "an.nguyen@example.edu"}),
            "constraint",
        ),
        (lambda db: db.aggregate("students", "median", column="id"), "Unsupported aggregate metric"),
        (lambda db: db.aggregate("students", "avg"), "requires a column"),
        (lambda db: db.aggregate("students", "avg", column="name"), "numeric column"),
    ],
)
def test_validation_errors_are_clear(adapter, call, message):
    with pytest.raises(ValidationError, match=message):
        call(adapter)


def test_schema_helpers(adapter):
    database_schema = adapter.get_database_schema()
    table_schema = adapter.get_table_schema("students")

    assert set(database_schema["tables"]) == {"courses", "enrollments", "students"}
    assert table_schema["table"] == "students"
    assert any(column["name"] == "cohort" for column in table_schema["columns"])
