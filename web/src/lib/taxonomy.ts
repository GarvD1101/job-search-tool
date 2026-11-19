export const ROLES = [
  { value: "software_dev", label: "Software Dev" },
  { value: "data_analytics", label: "Data & Analytics" },
  { value: "ml_ai", label: "AI & ML" },
  { value: "it_devops_security", label: "DevOps & IT Security" },
  { value: "qa_testing", label: "QA & Testing" },
  { value: "product_management", label: "Product Management" },
  { value: "design", label: "Design & Creative" },
  { value: "marketing", label: "Marketing & Growth" },
  { value: "sales_bd", label: "Sales & BD" },
  { value: "customer_support", label: "Customer Support" },
  { value: "admin_back_office", label: "Admin & Back Office" },
  { value: "hr_recruitment", label: "HR & Recruitment" },
  { value: "finance_banking", label: "Finance & Banking" },
  { value: "operations_logistics", label: "Operations & Logistics" },
  { value: "content_writing", label: "Content & Writing" },
  { value: "research", label: "Research & Science" },
  { value: "teaching_education", label: "Teaching & Education" },
  { value: "core_engineering", label: "Core Engineering" },
  { value: "healthcare", label: "Healthcare & Pharma" },
  { value: "legal_compliance", label: "Legal & Compliance" },
  { value: "hospitality_retail", label: "Hospitality & Retail" },
  { value: "other", label: "Other" },
] as const;

export const CITIES = [
  { value: "bengaluru", label: "Bengaluru" },
  { value: "hyderabad", label: "Hyderabad" },
  { value: "pune", label: "Pune" },
  { value: "mumbai", label: "Mumbai" },
  { value: "delhi_ncr", label: "Delhi NCR" },
  { value: "chennai", label: "Chennai" },
  { value: "kolkata", label: "Kolkata" },
  { value: "ahmedabad", label: "Ahmedabad" },
  { value: "other_india", label: "Other India" },
  { value: "remote", label: "Remote" },
] as const;

export const POST_TYPES = [
  { value: "job", label: "Job" },
  { value: "internship", label: "Internship" },
  { value: "trainee", label: "Trainee" },
] as const;

export const ALLOWED_ROLE_VALUES = new Set(ROLES.map((r) => r.value));
export const ALLOWED_CITY_VALUES = new Set([
  ...CITIES.map((c) => c.value),
  "unknown",
]);
export const ALLOWED_POST_TYPE_VALUES = new Set(POST_TYPES.map((p) => p.value));

export function formatRole(role: string | null): string {
  if (!role) return "General";
  const found = ROLES.find((r) => r.value === role);
  return found ? found.label : role.replace(/_/g, " ");
}

export function formatCity(city: string | null, isRemote?: boolean): string {
  if (isRemote || city === "remote") return "Remote";
  if (!city || city === "unknown") return "India";
  const found = CITIES.find((c) => c.value === city);
  return found ? found.label : city.replace(/_/g, " ");
}

export function formatPostType(type: string | null): string {
  if (!type) return "Job";
  const found = POST_TYPES.find((p) => p.value === type);
  return found ? found.label : type.replace(/_/g, " ");
}
