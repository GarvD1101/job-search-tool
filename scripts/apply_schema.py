import os
import sys
from pathlib import Path

import psycopg


def get_db_url() -> str | None:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if db_url:
        return db_url

    # Fallback for Windows if environment variable was set in registry but not yet in process env
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                val, _ = winreg.QueryValueEx(key, "SUPABASE_DB_URL")
                if val:
                    return str(val)
        except OSError:
            pass
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            ) as key:
                val, _ = winreg.QueryValueEx(key, "SUPABASE_DB_URL")
                if val:
                    return str(val)
        except OSError:
            pass

    return None


def apply_schema() -> int:
    db_url = get_db_url()
    if not db_url:
        print("SUPABASE_DB_URL not set. Skipping schema application cleanly.")
        return 0

    schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
    if not schema_path.exists():
        print(f"Error: Schema file not found at {schema_path}", file=sys.stderr)
        return 1

    sql = schema_path.read_text(encoding="utf-8")

    print("Connecting to Supabase Postgres (Session pooler)...")
    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                print("Connected successfully. Applying schema...")
                cur.execute(sql)

                # Query tables in public schema
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                    """
                )
                tables = [row[0] for row in cur.fetchall()]

                # Query row level security status
                cur.execute(
                    """
                    SELECT tablename, rowsecurity
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename;
                    """
                )
                rls_info = {row[0]: row[1] for row in cur.fetchall()}

                print("Schema applied successfully.")
                print("Public tables in database:")
                for table in tables:
                    rls_status = "RLS enabled" if rls_info.get(table) else "RLS disabled"
                    print(f"  - {table} ({rls_status})")

        return 0
    except Exception as exc:
        # Sanitize error to avoid printing connection strings containing credentials
        err_msg = str(exc)
        if "@" in err_msg:
            err_msg = "Database connection error (credentials masked)"
        print(f"Failed to apply schema: {err_msg}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(apply_schema())
