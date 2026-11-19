import { getCachedJobs } from "@/lib/jobs";
import { cleanJobSnippet, formatLocation } from "@/lib/formatters";
import { formatCity } from "@/lib/taxonomy";
import JobExplorer from "@/components/JobExplorer";

interface PageProps {
  searchParams: {
    q?: string;
    role?: string;
    city?: string;
    post_type?: string;
    source?: string;
    page?: string;
  };
}

export const dynamic = "force-dynamic";

export default async function HomePage({ searchParams }: PageProps) {
  const page = parseInt(searchParams.page || "1", 10) || 1;

  const data = await getCachedJobs({
    q: searchParams.q,
    role: searchParams.role,
    city: searchParams.city,
    post_type: searchParams.post_type,
    source: searchParams.source,
    page,
    pageSize: 20,
  });

  const sanitizedJobs = data.items.map((job) => ({
    ...job,
    location_text: formatLocation(
      job.location_text || formatCity(job.city, job.is_remote)
    ),
    description: cleanJobSnippet(job.description),
  }));

  return (
    <JobExplorer
      jobs={sanitizedJobs}
      total={data.total}
      page={data.page}
      pageSize={data.pageSize}
      totalPages={data.totalPages}
    />
  );
}
