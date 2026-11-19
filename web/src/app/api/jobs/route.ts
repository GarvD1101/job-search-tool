import { NextRequest, NextResponse } from "next/server";
import { getJobs } from "@/lib/jobs";
import {
  ALLOWED_CITY_VALUES,
  ALLOWED_POST_TYPE_VALUES,
  ALLOWED_ROLE_VALUES,
} from "@/lib/taxonomy";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;

    const q = searchParams.get("q") || undefined;
    const roleParam = searchParams.get("role") || undefined;
    const cityParam = searchParams.get("city") || undefined;
    const postTypeParam = searchParams.get("post_type") || undefined;
    const sourceParam = searchParams.get("source") || undefined;

    // Validate enum inputs
    const role =
      roleParam && ALLOWED_ROLE_VALUES.has(roleParam as any)
        ? roleParam
        : undefined;
    const city =
      cityParam && ALLOWED_CITY_VALUES.has(cityParam as any)
        ? cityParam
        : undefined;
    const post_type =
      postTypeParam && ALLOWED_POST_TYPE_VALUES.has(postTypeParam as any)
        ? postTypeParam
        : undefined;

    const page = Math.max(1, parseInt(searchParams.get("page") || "1", 10));
    const rawPageSize = parseInt(searchParams.get("pageSize") || "20", 10);
    const pageSize = Math.min(50, Math.max(1, isNaN(rawPageSize) ? 20 : rawPageSize));

    const response = await getJobs({
      q,
      role,
      city,
      post_type,
      source: sourceParam,
      page,
      pageSize,
    });

    return NextResponse.json(response, {
      status: 200,
      headers: {
        "Cache-Control": "public, s-maxage=300, stale-while-revalidate=600",
      },
    });
  } catch (error: any) {
    console.error("API /api/jobs error:", error);
    return NextResponse.json(
      { error: "Internal Server Error", message: error.message },
      { status: 500 }
    );
  }
}
