export interface Job {
  id: number;
  source: string;
  source_id: string;
  dedup_key?: string;
  canonical_key: string;
  title: string;
  company: string;
  location_text: string;
  description: string | null;
  url: string;
  origin_site: string;
  status: string;
  post_type: string | null;
  is_fresher: boolean | null;
  role: string | null;
  city: string | null;
  is_remote: boolean;
  posted_at: string | null;
  first_seen_at: string;
}

export interface JobsQueryOptions {
  q?: string;
  role?: string;
  city?: string;
  post_type?: string;
  source?: string;
  page?: number;
  pageSize?: number;
}

export interface JobsResponse {
  items: Job[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface RunInfo {
  id: number;
  trigger: string;
  started_at: string;
  finished_at: string | null;
  status: string;
}

export interface StatsData {
  total_active: number;
  total_raw: number;
  total_duplicates: number;
  non_llm_share_pct: number;
  source_counts: { name: string; count: number }[];
  origin_counts: { name: string; count: number }[];
  role_counts: { name: string; count: number }[];
  city_counts: { name: string; count: number }[];
  reject_reasons: { reason: string; count: number }[];
  llm_usage: {
    total_calls: number;
    input_tokens: number;
    output_tokens: number;
    reasoning_tokens: number;
    total_tokens: number;
    list_price_cost: number;
  };
  last_run: RunInfo | null;
  runs_by_event?: { event: string; count: number }[];
  latest_scheduled_run?: string | null;
}
