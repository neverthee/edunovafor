import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clear AI chat history records from the EduNova SQLite database."
    )
    parser.add_argument(
        "--db",
        default="backend/database/eduNova.sqlite",
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a timestamped database backup before deletion.",
    )
    parser.add_argument(
        "--vacuum",
        action="store_true",
        help="Run VACUUM after deletion to reclaim SQLite file space.",
    )
    return parser.parse_args()


def ensure_database_exists(db_path: Path) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")


def backup_database(db_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_name(f"{db_path.stem}.chat-history-backup-{timestamp}{db_path.suffix}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def main() -> int:
    args = parse_args()
    db_path = Path(args.db).resolve()
    ensure_database_exists(db_path)

    if not args.no_backup:
        backup_path = backup_database(db_path)
        print(f"Backup created: {backup_path}")

    connection = sqlite3.connect(db_path)
    try:
        if not table_exists(connection, "chat_history"):
            raise RuntimeError("Table 'chat_history' does not exist in the selected database.")

        before_count = connection.execute("SELECT COUNT(*) FROM chat_history").fetchone()[0]
        print(f"Chat history rows before cleanup: {before_count}")

        connection.execute("DELETE FROM chat_history")
        connection.commit()

        if args.vacuum:
            connection.execute("VACUUM")

        after_count = connection.execute("SELECT COUNT(*) FROM chat_history").fetchone()[0]
        print(f"Chat history rows after cleanup: {after_count}")
        print(f"Deleted rows: {before_count - after_count}")
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
