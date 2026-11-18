import psycopg

from scripts.apply_schema import get_db_url


def main():
    db_url = get_db_url()
    if not db_url:
        print("Error: SUPABASE_DB_URL is not set.")
        return 1

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT source, COUNT(*) FROM raw_posts GROUP BY source ORDER BY source;")
            before = cur.fetchall()
            print("Counts before cleanup:", before)

            cur.execute("DELETE FROM raw_posts WHERE source = 'greenhouse';")
            deleted = cur.rowcount
            print(f"Deleted greenhouse rows: {deleted}")

            cur.execute("SELECT source, COUNT(*) FROM raw_posts GROUP BY source ORDER BY source;")
            after = cur.fetchall()
            print("Counts after cleanup:", after)

    return 0


if __name__ == "__main__":
    main()
