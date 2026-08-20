"""Create a shareable demo database from the local EduNova SQLite database."""

from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "eduNova.sqlite"
DEFAULT_OUTPUT = ROOT / "eduNova.demo.sqlite"
PERSONAL_TABLES = (
    "assessment_publish_classes",
    "assessment_submissions",
    "chat_history",
    "course_students",
    "knowledge_base_queue",
    "learning_record",
    "student_ai_quizzes",
    "student_answers",
    "teacher_class_students",
    "teacher_classes",
)
TEXT_COLUMNS = {
    "assessments": ("title", "description", "questions"),
    "course": ("name", "description"),
    "material": ("title", "content"),
}
REDACTIONS = (
    (re.compile(r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"), "<redacted-email>"),
    (re.compile(r"(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)"), "<redacted-phone>"),
    (re.compile(r"(?<!\d)\d{17}[\dXx](?!\w)"), "<redacted-id>"),
    (re.compile(r"(?i)[A-Z]:[\\/][^\s\"']+"), "<redacted-path>"),
)


def redact(value: str | None) -> str | None:
    if value is None:
        return None
    for pattern, replacement in REDACTIONS:
        value = pattern.sub(replacement, value)
    return value


def sanitize(source: Path, output: Path) -> None:
    if source.resolve() == output.resolve():
        raise ValueError("The output database must not overwrite the source database.")
    if not source.is_file():
        raise FileNotFoundError(source)

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    connection = sqlite3.connect(output)
    try:
        with connection:
            for table in PERSONAL_TABLES:
                connection.execute(f'DELETE FROM "{table}"')

            connection.execute("UPDATE course SET teacher_id = 2, cover_image = NULL")
            connection.execute("UPDATE assessments SET created_by = 2")
            connection.execute(
                "UPDATE material SET file_path = NULL, preview_file_path = NULL, "
                "preview_error = NULL, file_hash = NULL, external_url = NULL"
            )
            connection.execute("DELETE FROM user")
            connection.executemany(
                "INSERT INTO user "
                "(id, username, email, password_hash, full_name, role, is_active) "
                "VALUES (?, ?, ?, ?, ?, ?, 1)",
                (
                    (1, "demo_admin", "admin@example.com", generate_password_hash("admin123"), "演示管理员", "admin"),
                    (2, "demo_teacher", "teacher@example.com", generate_password_hash("teacher123"), "演示教师", "teacher"),
                    (3, "demo_student", "student@example.com", generate_password_hash("student123"), "演示学生", "student"),
                ),
            )
            for table, columns in TEXT_COLUMNS.items():
                for column in columns:
                    rows = connection.execute(
                        f'SELECT id, "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'
                    ).fetchall()
                    connection.executemany(
                        f'UPDATE "{table}" SET "{column}" = ? WHERE id = ?',
                        ((redact(value), row_id) for row_id, value in rows),
                    )
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    sanitize(args.source, args.output)
    print(f"Created sanitized demo database: {args.output}")


if __name__ == "__main__":
    main()
