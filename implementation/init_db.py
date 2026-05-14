from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "sqlite_lab.db"


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0)
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'dropped')),
    UNIQUE (student_id, course_id)
);
"""


SEED_SQL = """
INSERT INTO students (name, cohort, email) VALUES
    ('An Nguyen', 'A1', 'an.nguyen@example.edu'),
    ('Binh Tran', 'A1', 'binh.tran@example.edu'),
    ('Chi Pham', 'B2', 'chi.pham@example.edu'),
    ('Dung Le', 'B2', 'dung.le@example.edu'),
    ('Mai Hoang', 'C3', 'mai.hoang@example.edu');

INSERT INTO courses (code, title, credits) VALUES
    ('PY101', 'Python Foundations', 3),
    ('DB201', 'Relational Databases', 4),
    ('AI301', 'Applied AI Systems', 4);

INSERT INTO enrollments (student_id, course_id, score, status) VALUES
    (1, 1, 91.5, 'completed'),
    (1, 2, 87.0, 'completed'),
    (2, 1, 78.0, 'completed'),
    (2, 3, 84.5, 'active'),
    (3, 2, 92.0, 'completed'),
    (3, 3, 88.5, 'active'),
    (4, 1, 69.0, 'completed'),
    (4, 2, 73.5, 'completed'),
    (5, 3, 95.0, 'active');
"""


def create_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    """Create a fresh SQLite database with deterministic seed data."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.executescript(SEED_SQL)
        connection.commit()

    return path


if __name__ == "__main__":
    created_path = create_database()
    print(f"Created SQLite lab database at {created_path}")
