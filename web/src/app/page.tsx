import { getCachedJobs } from "@/lib/jobs";
import JobCard from "@/components/JobCard";
import Pagination from "@/components/Pagination";
import SearchAndFilters from "@/components/SearchAndFilters";

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

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Find Fresher & Internship Jobs in India
        </h1>
        <p className="text-sm text-slate-600 mt-1.5">
          Filtered and verified for 0-1 years experience, updated every day from direct company boards and aggregator APIs.
        </p>
      </div>

      <SearchAndFilters totalCount={data.total} />

      {data.items.length > 0 ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.items.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>

          <Pagination
            currentPage={data.page}
            totalPages={data.totalPages}
          />
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-dashed border-slate-300 p-12 text-center my-8">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3 text-slate-400 font-bold text-xl">
            ?
          </div>
          <h3 className="text-base font-semibold text-slate-900">
            No matching jobs found
          </h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Try broadening your search term, clearing your role or city filter, or checking back after tomorrow morning's daily refresh.
          </p>
        </div>
      )}
    </div>
  );
}
