"""
Raw SQL access to Nova's Postgres database (Supabase).

The supabase client the DAOs use speaks PostgREST, which cannot run
arbitrary SQL, so this service connects straight to Postgres through
Supabase's connection pooler. It is exposed to the agent loop as the
run_sql tool, with the blast radius kept small:

- queries run in a READ ONLY transaction unless the caller explicitly
  opts into writes (enforced by Postgres, not by parsing);
- schema/privilege statements (CREATE/ALTER/DROP/...) are refused
  outright — those belong in the Supabase SQL editor with a human;
- results are capped so a huge table can't flood the model's context.
"""

import os
import re
from typing import Any, ClassVar

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

_ROW_LIMIT = 200
_STATEMENT_TIMEOUT_MS = 15_000

# Statements that change schema or privileges. run_sql is a data tool;
# anything structural should be reviewed and run by the user in the
# Supabase SQL editor instead. Word-boundary match, so column names like
# created_at don't trip it (a string literal containing one of these words
# can — rephrase the query or run it manually in that rare case).
_DDL_PATTERN = re.compile(
    r"\b(create|alter|drop|truncate|grant|revoke|reindex|vacuum)\b",
    re.IGNORECASE,
)


def _jsonable(value: Any) -> Any:
    """Tool results are json.dumps'd by the agent loop; keep values safe."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)  # datetime, UUID, Decimal, memoryview, ...


class SQLService:
    # One engine per process, not per tool call: ToolService builds a fresh
    # service instance for every call, and reconnecting each time would
    # hammer the pooler.
    _engine: ClassVar[Engine | None] = None

    @staticmethod
    def _database_url() -> str:
        """
        Resolve the direct-Postgres DSN.

        SUPABASE_DB_URL wins when set. Otherwise the DSN is derived from
        SUPABASE_URL + SUPABASE_PASSWORD via the session pooler — the
        db.<ref>.supabase.co direct host is IPv6-only, so the pooler is
        what actually works from most networks.
        """
        explicit = os.getenv("SUPABASE_DB_URL")
        if explicit:
            if explicit.startswith("postgresql://"):
                explicit = explicit.replace("postgresql://", "postgresql+psycopg2://", 1)
            return explicit

        supabase_url = os.getenv("SUPABASE_URL") or ""
        match = re.match(r"https://([^.]+)\.supabase\.co", supabase_url)
        password = os.getenv("SUPABASE_PASSWORD")
        if not match or not password:
            raise RuntimeError(
                "run_sql needs SUPABASE_DB_URL, or SUPABASE_URL plus "
                "SUPABASE_PASSWORD, in the environment."
            )

        ref = match.group(1)
        host = os.getenv("SUPABASE_DB_HOST", "aws-0-us-west-1.pooler.supabase.com")
        return f"postgresql+psycopg2://postgres.{ref}:{password}@{host}:5432/postgres"

    def _get_engine(self) -> Engine:
        if SQLService._engine is None:
            SQLService._engine = create_engine(
                self._database_url(),
                pool_size=2,
                max_overflow=2,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 10},
            )
        return SQLService._engine

    def run_sql(self, sql: str, allow_writes: bool = False) -> dict[str, Any]:
        """
        Run one SQL statement and return its result.

        Read-only unless allow_writes is True; Postgres itself rejects any
        write attempted in the read-only transaction, so there is no SQL
        parsing to sneak past. SELECTs return {columns, rows, row_count,
        truncated}; writes return {status, rows_affected}.
        """
        sql = (sql or "").strip().rstrip(";")
        if not sql:
            raise ValueError("A SQL statement is required.")

        if _DDL_PATTERN.search(sql):
            raise ValueError(
                "run_sql does not execute schema or privilege statements "
                "(CREATE/ALTER/DROP/TRUNCATE/GRANT/REVOKE/REINDEX/VACUUM). "
                "Ask the user to run those in the Supabase SQL editor."
            )

        engine = self._get_engine()
        with engine.connect() as conn:
            if not allow_writes:
                # Must be the first statement of the (autobegun) transaction.
                conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text(f"SET LOCAL statement_timeout = {_STATEMENT_TIMEOUT_MS}"))

            result = conn.execute(text(sql))

            if result.returns_rows:
                columns = list(result.keys())
                fetched = result.mappings().fetchmany(_ROW_LIMIT + 1)
                truncated = len(fetched) > _ROW_LIMIT
                rows = [
                    {key: _jsonable(value) for key, value in row.items()}
                    for row in fetched[:_ROW_LIMIT]
                ]
                payload: dict[str, Any] = {
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "truncated": truncated,
                }
                if truncated:
                    payload["note"] = (
                        f"Only the first {_ROW_LIMIT} rows are returned; "
                        "narrow the query for the rest."
                    )
            else:
                payload = {"status": "ok", "rows_affected": result.rowcount}

            conn.commit()

        return payload
