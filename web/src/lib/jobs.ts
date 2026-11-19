import { unstable_cache } from "next/cache";
import { query } from "./db";
import {
  ALLOWED_CITY_VALUES,
  ALLOWED_POST_TYPE_VALUES,
  ALLOWED_ROLE_VALUES,
} from "./taxonomy";
import { Job, JobsQueryOptions, JobsResponse, RunInfo, StatsData } from "./types";

export async function getJobs(options: JobsQueryOptions): Promise<JobsResponse> {
  const page = Math.max(1, Number(options.page) || 1);
  const pageSize = Math.min(50, Math.max(1, Number(options.pageSize) || 20));
  const offset = (page - 1) * pageSize;

  try {
    const conditions: string[] = ["status = 'active'"];
    const params: (string | number | boolean | null | undefined)[] = [];
    let paramIdx = 1;

    let searchQuery = "";
    if (options.q && options.q.trim()) {
      searchQuery = options.q.trim();
      conditions.push(`fts @@ websearch_to_tsquery('english', $${paramIdx})`);
      params.push(searchQuery);
      paramIdx++;
    }

    if (options.role && ALLOWED_ROLE_VALUES.has(options.role as any)) {
      conditions.push(`role = $${paramIdx}`);
      params.push(options.role);
      paramIdx++;
    }

    if (options.city && ALLOWED_CITY_VALUES.has(options.city as any)) {
      if (options.city === "remote") {
        conditions.push(`(city = 'remote' OR is_remote = TRUE)`);
      } else {
        conditions.push(`city = $${paramIdx}`);
        params.push(options.city);
        paramIdx++;
      }
    }

    if (options.post_type && ALLOWED_POST_TYPE_VALUES.has(options.post_type as any)) {
      conditions.push(`post_type = $${paramIdx}`);
      params.push(options.post_type);
      paramIdx++;
    }

    if (options.source && options.source.trim()) {
      conditions.push(`(origin_site = $${paramIdx} OR source = $${paramIdx})`);
      params.push(options.source.trim());
      paramIdx++;
    }

    const whereClause = conditions.join(" AND ");

    // Order clause
    let orderClause = "ORDER BY posted_at DESC NULLS LAST, first_seen_at DESC";
    if (searchQuery) {
      orderClause = `ORDER BY ts_rank(fts, websearch_to_tsquery('english', $1)) DESC, posted_at DESC NULLS LAST, first_seen_at DESC`;
    }

    // Single query for rows and total using window function count(*) over()
    const selectSql = `
      SELECT
        id, source, source_id, dedup_key, canonical_key, title, company, location_text, description,
        url, origin_site, status, post_type, is_fresher,
        role, city, is_remote, posted_at, first_seen_at,
        count(*) over()::int as full_count
      FROM jobs
      WHERE ${whereClause}
      ${orderClause}
      LIMIT $${paramIdx} OFFSET $${paramIdx + 1};
    `;

    const selectParams = [...params, pageSize, offset];
    const jobsRes = await query<Job & { full_count?: number }>(selectSql, selectParams);

    let total = 0;
    if (jobsRes.rows.length > 0) {
      total = jobsRes.rows[0].full_count || 0;
    } else if (offset > 0) {
      // Offset was beyond total results; query count separately
      const countSql = `SELECT count(*)::int as total FROM jobs WHERE ${whereClause};`;
      const countRes = await query<{ total: number }>(countSql, params);
      total = countRes.rows[0]?.total || 0;
    }

    return {
      items: jobsRes.rows.map(({ full_count, ...job }) => job as Job),
      total,
      page,
      pageSize,
      totalPages: Math.ceil(total / pageSize) || 1,
    };
  } catch (err) {
    console.warn("Could not query jobs:", err);
    return {
      items: [],
      total: 0,
      page,
      pageSize,
      totalPages: 1,
    };
  }
}

export const getCachedJobs = (options: JobsQueryOptions): Promise<JobsResponse> => {
  const cacheKey = [
    "jobs",
    options.q || "",
    options.role || "",
    options.city || "",
    options.post_type || "",
    options.source || "",
    String(options.page || 1),
    String(options.pageSize || 20),
  ];

  return unstable_cache(
    async () => getJobs(options),
    cacheKey,
    { revalidate: 300, tags: ["jobs"] }
  )();
};


async function fetchLastRefresh(): Promise<RunInfo | null> {
  try {
    const sql = `
      SELECT id, trigger, started_at, finished_at, status
      FROM runs
      WHERE status = 'success'
      ORDER BY id DESC
      LIMIT 1;
    `;
    const res = await query<RunInfo>(sql);
    return res.rows[0] || null;
  } catch (err) {
    console.warn("Could not query last refresh:", err);
    return null;
  }
}

export const getLastRefresh = unstable_cache(
  fetchLastRefresh,
  ["last-refresh"],
  { revalidate: 300, tags: ["runs"] }
);

export async function getStats(): Promise<StatsData> {
  try {
    // Parallel query execution safe for connection pool
    const [
      activeRes,
      rawRes,
      dupRes,
      ruleRejRes,
      sourceRes,
      originRes,
      roleRes,
      cityRes,
      reasonsRes,
      llmRes,
      lastRunRes,
      runsByEventRes,
      latestSchedRes,
    ] = await Promise.all([
      query<{ count: number }>("SELECT count(*)::int FROM jobs WHERE status = 'active';"),
      query<{ count: number }>("SELECT count(*)::int FROM raw_posts;"),
      query<{ count: number }>("SELECT count(*)::int FROM jobs WHERE status = 'duplicate';"),
      query<{ count: number }>(
        "SELECT count(*)::int FROM jobs WHERE status = 'rejected' AND tag_source = 'rule';"
      ),
      query<{ name: string; count: number }>(
        "SELECT source as name, count(*)::int FROM jobs WHERE status = 'active' GROUP BY source ORDER BY count DESC;"
      ),
      query<{ name: string; count: number }>(
        "SELECT origin_site as name, count(*)::int FROM jobs WHERE status = 'active' GROUP BY origin_site ORDER BY count DESC LIMIT 15;"
      ),
      query<{ name: string; count: number }>(
        "SELECT role as name, count(*)::int FROM jobs WHERE status = 'active' AND role IS NOT NULL GROUP BY role ORDER BY count DESC;"
      ),
      query<{ name: string; count: number }>(
        "SELECT city as name, count(*)::int FROM jobs WHERE status = 'active' AND city IS NOT NULL GROUP BY city ORDER BY count DESC;"
      ),
      query<{ reason: string; count: number }>(
        "SELECT COALESCE(rule_reason, 'unspecified') as reason, count(*)::int FROM jobs WHERE status = 'rejected' GROUP BY rule_reason ORDER BY count DESC;"
      ),
      query<{
        total_calls: number;
        input_tokens: number;
        output_tokens: number;
        reasoning_tokens: number;
      }>(
        `SELECT
          count(*)::int as total_calls,
          coalesce(sum(input_tokens), 0)::bigint as input_tokens,
          coalesce(sum(output_tokens), 0)::bigint as output_tokens,
          coalesce(sum(reasoning_tokens), 0)::bigint as reasoning_tokens
        FROM llm_calls;`
      ),
      getLastRefresh(),
      query<{ event: string; count: number }>(
        "SELECT trigger as event, count(*)::int FROM runs GROUP BY trigger ORDER BY count DESC;"
      ),
      query<{ started_at: string }>(
        "SELECT started_at FROM runs WHERE trigger = 'schedule' ORDER BY id DESC LIMIT 1;"
      ),
    ]);

    const total_active = activeRes.rows[0]?.count || 0;
    const total_raw = rawRes.rows[0]?.count || 0;
    const total_duplicates = dupRes.rows[0]?.count || 0;
    const rule_rejects = ruleRejRes.rows[0]?.count || 0;

    // Share of fetched posts that never reached the LLM (rule rejects + duplicates / total raw posts)
    const non_llm_posts = rule_rejects + total_duplicates;
    const non_llm_share_pct =
      total_raw > 0 ? Math.round((non_llm_posts / total_raw) * 1000) / 10 : 0.0;

    // LLM cost projection based on list price for openai/gpt-oss-20b ($0.075/1M in, $0.30/1M out)
    const inpTok = Number(llmRes.rows[0]?.input_tokens || 0);
    const outTok = Number(llmRes.rows[0]?.output_tokens || 0);
    const reasTok = Number(llmRes.rows[0]?.reasoning_tokens || 0);
    const totalCalls = Number(llmRes.rows[0]?.total_calls || 0);
    const list_price_cost =
      Math.round(((inpTok * 0.075 + outTok * 0.3) / 1_000_000) * 10000) / 10000;

    return {
      total_active,
      total_raw,
      total_duplicates,
      non_llm_share_pct,
      source_counts: sourceRes.rows,
      origin_counts: originRes.rows,
      role_counts: roleRes.rows,
      city_counts: cityRes.rows,
      reject_reasons: reasonsRes.rows,
      llm_usage: {
        total_calls: totalCalls,
        input_tokens: inpTok,
        output_tokens: outTok,
        reasoning_tokens: reasTok,
        total_tokens: inpTok + outTok,
        list_price_cost,
      },
      last_run: lastRunRes,
      runs_by_event: runsByEventRes.rows,
      latest_scheduled_run: latestSchedRes.rows[0]?.started_at || null,
    };
  } catch (err) {
    console.warn("Could not query stats:", err);
    return {
      total_active: 0,
      total_raw: 0,
      total_duplicates: 0,
      non_llm_share_pct: 0,
      source_counts: [],
      origin_counts: [],
      role_counts: [],
      city_counts: [],
      reject_reasons: [],
      llm_usage: {
        total_calls: 0,
        input_tokens: 0,
        output_tokens: 0,
        reasoning_tokens: 0,
        total_tokens: 0,
        list_price_cost: 0,
      },
      last_run: null,
      runs_by_event: [],
      latest_scheduled_run: null,
    };
  }
}
