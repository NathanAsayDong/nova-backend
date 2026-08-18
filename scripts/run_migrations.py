"""
Apply the SQL migrations in scripts/migrations/ in filename order.

SQLService.run_sql deliberately takes one statement at a time, so it can't run
a migration file; this connects with the same resolved DSN and executes each
file as a whole script, letting the file's own begin/commit bound it.

Every migration is written to be idempotent (add column if not exists, guarded
renames), so re-running this is safe and is the intended way to catch a
database up.

Run with:
    uv run python scripts/run_migrations.py            # apply all
    uv run python scripts/run_migrations.py --dry-run  # show what would run
    uv run python scripts/run_migrations.py 002        # apply matching files only
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

from sqlalchemy import create_engine, text  # noqa: E402

from src.service.sql_service import SQLService  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def migration_files(selector: str | None) -> list[Path]:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if selector:
        files = [path for path in files if selector in path.name]
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "selector",
        nargs="?",
        help="Only run migrations whose filename contains this string.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the statements that would run without executing them.",
    )
    args = parser.parse_args()

    files = migration_files(args.selector)
    if not files:
        print(f"No migrations found in {MIGRATIONS_DIR}.")
        return 1

    if args.dry_run:
        for path in files:
            print(f"\n===== {path.name} =====")
            print(path.read_text())
        return 0

    dsn = SQLService._database_url()
    # Autocommit at the driver level so each file's own BEGIN/COMMIT is what
    # bounds its transaction, and so statements outside one (NOTIFY) still land.
    engine = create_engine(dsn, future=True).execution_options(
        isolation_level="AUTOCOMMIT"
    )

    failures = 0
    with engine.connect() as conn:
        for path in files:
            print(f"Applying {path.name} ...", end=" ", flush=True)
            try:
                conn.exec_driver_sql(path.read_text())
                print("ok")
            except Exception as exc:
                failures += 1
                print("FAILED")
                print(f"  {type(exc).__name__}: {exc}")

        # Belt and braces: the files ask PostgREST to reload, but a failed file
        # may have skipped it, and a stale cache looks exactly like a missing
        # column to the DAOs.
        try:
            conn.exec_driver_sql("notify pgrst, 'reload schema'")
        except Exception as exc:
            print(f"Could not signal a PostgREST schema reload: {exc}")

    if failures:
        print(f"\n{failures} migration(s) failed.")
        return 1

    print("\nAll migrations applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
