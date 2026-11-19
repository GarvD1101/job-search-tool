/**
 * Display-Layer Data Sanitization & Formatting Utilities
 *
 * Cleans scraper artifacts, normalizes location strings, formats financial metrics,
 * and standardizes telemetry audit codes for the Industrial Swiss Grid interface.
 */

const CITY_ALIASES: Record<string, string> = {
  bangalore: "bengaluru",
  bengaluru: "bengaluru",
  kolkatta: "kolkata",
  kolkata: "kolkata",
  bombay: "mumbai",
  mumbai: "mumbai",
  madras: "chennai",
  chennai: "chennai",
  delhi: "delhi_ncr",
  "new delhi": "delhi_ncr",
  "delhi ncr": "delhi_ncr",
  gurugram: "delhi_ncr",
  gurgaon: "delhi_ncr",
  noida: "delhi_ncr",
  hyderabad: "hyderabad",
  pune: "pune",
  india: "india",
};

/**
 * Normalizes location strings and resolves duplicate/noisy combinations.
 * Examples:
 * - "Mumbai (Mumbai)" -> "Mumbai"
 * - "Bengaluru (Bangalore)" -> "Bengaluru"
 * - "Mumbai (Kharghar)" -> "Mumbai · Kharghar"
 * - "Remote (work from home)" -> "Remote"
 */
export function formatLocation(raw: string | null | undefined): string {
  if (!raw) return "India";
  const trimmed = raw.trim();
  if (!trimmed) return "India";

  // Check for "Primary (Secondary)" pattern
  const parenMatch = trimmed.match(/^([^()]+?)\s*\(([^()]+)\)$/);
  if (parenMatch) {
    let primary = parenMatch[1].trim();
    let secondary = parenMatch[2].trim();

    // Standardize common typos
    if (/^kolkatta$/i.test(primary)) primary = "Kolkata";
    if (/^kolkatta$/i.test(secondary)) secondary = "Kolkata";
    if (/^bangalore$/i.test(primary)) primary = "Bengaluru";
    if (/^bangalore$/i.test(secondary)) secondary = "Bengaluru";

    const pNorm = primary.toLowerCase();
    const sNorm = secondary.toLowerCase();

    // Redundant secondary check
    if (
      pNorm === sNorm ||
      CITY_ALIASES[pNorm] === CITY_ALIASES[sNorm] ||
      (sNorm.includes("work from home") && pNorm === "remote") ||
      (sNorm.includes("anywhere in india") && pNorm === "remote") ||
      sNorm === "india"
    ) {
      return primary;
    }

    // Meaningful sub-locality
    return `${primary} · ${secondary}`;
  }

  // Check for "City, City" duplication (e.g. "Mumbai, Mumbai")
  const commaParts = trimmed.split(",").map((s) => s.trim()).filter(Boolean);
  if (commaParts.length === 2) {
    const c1 = commaParts[0].toLowerCase();
    const c2 = commaParts[1].toLowerCase();
    if (c1 === c2 || CITY_ALIASES[c1] === CITY_ALIASES[c2]) {
      return commaParts[0];
    }
  }

  return trimmed;
}

/**
 * Cleans scraper artifacts, leading markdown/punctuation, broken masks, and duplicate phrases.
 */
export function cleanJobSnippet(raw: string | null | undefined): string {
  if (!raw) return "";
  let text = raw.trim();

  // Strip leading ellipses, hashes, bullets, dashes, asterisks
  text = text.replace(/^[\.\s#•\-\*]+/, "");
  text = text.replace(/^(?:#+\s*)+/, "");

  // Remove empty or broken phone masks like "(***) )", "(***)", "***"
  text = text.replace(/\(\*+\)\s*\)?/g, "");
  text = text.replace(/\*+/g, "");

  // Collapse adjacent duplicated phrases (10-40 chars repeated twice)
  text = text.replace(/\b(.{10,40}?)\s+\1\b/gi, "$1");

  // Collapse excess whitespace
  text = text.replace(/\s+/g, " ").trim();

  return text;
}

/**
 * Formats numeric amounts to USD strings with strict prefix and no line breaks.
 * Examples: $10.59, $256.52, $0.0043
 */
export function formatUsd(amount: number, decimals = 2): string {
  if (typeof amount !== "number" || isNaN(amount)) return "$0.00";
  if (amount > 0 && amount < 0.01) {
    return `$${amount.toFixed(4)}`;
  }
  return `$${amount.toFixed(decimals)}`;
}

/**
 * Formats rejection reasons into structured telemetry codes and readable labels.
 */
export function formatRejectionReason(rawKey: string): {
  code: string;
  label: string;
  groupKey: string;
} {
  const key = (rawKey || "").trim();

  if (/^tier2_fuzzy_match_/i.test(key)) {
    return {
      groupKey: "FUZZY_DUP",
      code: "FUZZY_DUP",
      label: "Tier-2 Fuzzy Duplicate",
    };
  }

  switch (key) {
    case "seniority":
      return {
        groupKey: "SENIORITY",
        code: "SENIORITY",
        label: "Senior / Mid-Level Role",
      };
    case "experience_required":
      return {
        groupKey: "EXP_REQ",
        code: "EXP_REQ",
        label: "Prior Experience Required",
      };
    case "min_1_year_experience":
      return {
        groupKey: "MIN_1YR",
        code: "MIN_1YR",
        label: "Minimum 1+ Year Specified",
      };
    case "stale":
      return {
        groupKey: "STALE_POST",
        code: "STALE_POST",
        label: "Expired / Stale Listing",
      };
    case "unclear_fresher_fit":
      return {
        groupKey: "UNCLEAR_FIT",
        code: "UNCLEAR_FIT",
        label: "Unclear Entry-Level Fit",
      };
    case "not_a_job_post":
      return {
        groupKey: "NON_JOB",
        code: "NON_JOB",
        label: "Non-Job Content",
      };
    case "not_india":
      return {
        groupKey: "NON_INDIA",
        code: "NON_INDIA",
        label: "Outside India",
      };
    default: {
      const code = key.replace(/[^a-zA-Z0-9]/g, "_").toUpperCase().slice(0, 10);
      const label = key
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
      return {
        groupKey: code || "RULE_REJ",
        code: code || "RULE_REJ",
        label: label || "Rule Filter Rejection",
      };
    }
  }
}

/**
 * Consolidates origin board domains into clean display labels.
 */
export function normalizeOriginBoard(raw: string | null | undefined): string {
  if (!raw) return "Unknown Board";
  const lower = raw.toLowerCase().trim();
  if (lower === "greenhouse" || lower.includes("boards.greenhouse.io")) {
    return "boards.greenhouse.io (Direct ATS)";
  }
  if (lower === "jooble" || lower.includes("jooble.org")) {
    return "in.jooble.org (Aggregator)";
  }
  return raw;
}

/**
 * Returns 1-2 uppercase characters for technical company monogram badges.
 */
export function getCompanyMonogram(company: string | null | undefined): string {
  if (!company) return "FR";
  const cleaned = company.trim().replace(/[^a-zA-Z0-9\s]/g, "");
  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  if (words.length === 1 && words[0].length >= 2) {
    return words[0].slice(0, 2).toUpperCase();
  }
  if (words.length === 1 && words[0].length === 1) {
    return words[0].toUpperCase();
  }
  return "FR";
}
