import { Pool, QueryResult, QueryResultRow } from "pg";

let pool: Pool | null = null;

export function getPool(): Pool {
  if (!pool) {
    const connectionString =
      process.env.DATABASE_URL || process.env.SUPABASE_DB_URL;

    if (!connectionString) {
      throw new Error(
        "DATABASE_URL or SUPABASE_DB_URL environment variable is required."
      );
    }

    const isLocalhost =
      connectionString.includes("localhost") ||
      connectionString.includes("127.0.0.1");

    pool = new Pool({
      connectionString,
      max: 3,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 10000,
      ssl: isLocalhost ? false : { rejectUnauthorized: false },
    });

    pool.on("error", (err) => {
      console.error("Unexpected error on idle PostgreSQL client:", err);
    });
  }

  return pool;
}

/**
 * Execute parameterized SQL query safe for Supabase transaction poolers.
 * Never sets query 'name' to avoid prepared statement collisions in poolers.
 */
export async function query<T extends QueryResultRow = QueryResultRow>(
  text: string,
  params: (string | number | boolean | null | undefined)[] = []
): Promise<QueryResult<T>> {
  const p = getPool();
  return p.query<T>({ text, values: params });
}
