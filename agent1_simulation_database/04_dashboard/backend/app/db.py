from contextlib import contextmanager
from typing import Iterator

import psycopg2
import psycopg2.extras

from app.settings import settings


REQUIRED_TABLES = [
    "runs",
    "nodes_static",
    "global_timeseries",
    "cluster_timeseries",
    "events",
    "run_summary",
    "node_final_summary",
]


def _classify_operational_error(message: str) -> str:
    msg = message.lower()
    if "timed out" in msg or "timeout" in msg:
        return "timeout"
    if "connection refused" in msg:
        return "connection_refused"
    if "password authentication failed" in msg or "no pg_hba.conf entry" in msg:
        return "auth_failed"
    if "no route to host" in msg:
        return "connection_refused"
    return "query_error"


def _masked(value: str) -> str:
    if not value:
        return "missing"
    return "set"


def run_db_check() -> dict:
    result = {
        "env": {
            "PGHOST": settings.pg_host or "missing",
            "PGPORT": str(settings.pg_port) if settings.pg_port else "missing",
            "PGDATABASE": settings.pg_database or "missing",
            "PGUSER": settings.pg_user or "missing",
            "PGPASSWORD": _masked(settings.pg_password),
            "PGSCHEMA": settings.pg_schema or "missing",
            "PGCONNECT_TIMEOUT": str(settings.pg_connect_timeout),
            "PGSSLMODE": settings.pg_sslmode or "missing",
        },
        "tcp_connection": False,
        "authentication": False,
        "schema_exists": False,
        "search_path_set": False,
        "required_tables": {
            "missing": [],
            "present_count": 0,
        },
        "error_type": None,
        "error": None,
    }

    conn = None
    try:
        conn = psycopg2.connect(
            host=settings.pg_host,
            port=settings.pg_port,
            database=settings.pg_database,
            user=settings.pg_user,
            password=settings.pg_password,
            connect_timeout=settings.pg_connect_timeout,
            sslmode=settings.pg_sslmode,
        )
        result["tcp_connection"] = True
        result["authentication"] = True

        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {settings.pg_schema}, public")
            result["search_path_set"] = True
            
            cur.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (settings.pg_schema,))
            schema_ok = cur.fetchone() is not None
            result["schema_exists"] = schema_ok

            if schema_ok:
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    """,
                    (settings.pg_schema,),
                )
                present = {row[0] for row in cur.fetchall()}
                missing = [t for t in REQUIRED_TABLES if t not in present]
                result["required_tables"]["missing"] = missing
                result["required_tables"]["present_count"] = len(REQUIRED_TABLES) - len(missing)

    except psycopg2.OperationalError as exc:
        msg = str(exc).splitlines()[0]
        error_type = _classify_operational_error(msg)
        result["error_type"] = error_type
        # pg_hba/password failures indicate server is reachable but auth policy denied access.
        if error_type == "auth_failed":
            result["tcp_connection"] = True
            result["authentication"] = False
        result["error"] = msg
    except Exception as exc:  # pylint: disable=broad-except
        result["error_type"] = "query_error"
        result["error"] = str(exc)
    finally:
        if conn is not None:
            conn.close()

    return result


@contextmanager
def get_connection() -> Iterator[psycopg2.extensions.connection]:
    conn = psycopg2.connect(
        host=settings.pg_host,
        port=settings.pg_port,
        database=settings.pg_database,
        user=settings.pg_user,
        password=settings.pg_password,
        connect_timeout=settings.pg_connect_timeout,
        sslmode=settings.pg_sslmode,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {settings.pg_schema}, public")
        conn.commit()
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cursor(conn: psycopg2.extensions.connection) -> Iterator[psycopg2.extras.RealDictCursor]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield cur
    finally:
        cur.close()
