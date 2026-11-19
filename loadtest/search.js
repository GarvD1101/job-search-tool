import http from 'k6/http';
import { check, sleep } from 'k6';

// Target base URL configurable via environment variable
const BASE_URL = __ENV.TARGET_URL || 'http://localhost:3000';

// Scenario parameters
const SEARCH_TERMS = [
  '',
  'developer',
  'intern',
  'engineer',
  'analyst',
  'trainee',
  'associate',
  'frontend',
  'backend',
  'python',
  'java',
  'sales',
  'operations',
];

const ROLES = [
  '',
  'software_dev',
  'data_analytics',
  'ml_ai',
  'it_devops_security',
  'qa_testing',
  'sales_bd',
  'customer_support',
  'marketing',
  'hr_recruitment',
  'finance_banking',
  'operations_logistics',
];

const CITIES = [
  '',
  'bengaluru',
  'hyderabad',
  'pune',
  'mumbai',
  'delhi_ncr',
  'chennai',
  'kolkata',
  'remote',
];

const POST_TYPES = [
  '',
  'job',
  'internship',
  'trainee',
];

const PAGES = [1, 1, 1, 2, 2, 3, 4];

export const options = {
  stages: [
    { duration: '1m', target: 5 },   // Smoke test: 5 users for 1 minute
    { duration: '3m', target: 50 },  // Load test: 50 users for 3 minutes
    { duration: '30s', target: 0 },  // Clean ramp-down
  ],
  thresholds: {
    // 95% of requests must complete below 500 ms
    http_req_duration: ['p(95)<500'],
    // Error rate must stay strictly under 1%
    http_req_failed: ['rate<0.01'],
  },
};

function getRandomItem(array) {
  return array[Math.floor(Math.random() * array.length)];
}

export default function () {
  const term = getRandomItem(SEARCH_TERMS);
  const role = getRandomItem(ROLES);
  const city = getRandomItem(CITIES);
  const postType = getRandomItem(POST_TYPES);
  const page = getRandomItem(PAGES);

  const queryParts = [];
  if (term) queryParts.push(`q=${encodeURIComponent(term)}`);
  if (role) queryParts.push(`role=${encodeURIComponent(role)}`);
  if (city) queryParts.push(`city=${encodeURIComponent(city)}`);
  if (postType) queryParts.push(`post_type=${encodeURIComponent(postType)}`);
  if (page > 1) queryParts.push(`page=${page}`);

  const queryString = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';

  // 70% of traffic tests API endpoint, 30% tests server-rendered HTML page
  const testApi = Math.random() < 0.7;
  const endpoint = testApi ? `${BASE_URL}/api/jobs${queryString}` : `${BASE_URL}${queryString}`;

  const res = http.get(endpoint, {
    headers: {
      'Accept': testApi ? 'application/json' : 'text/html',
      'User-Agent': 'k6-loadtest-fresher-radar/1.0',
    },
    tags: { name: testApi ? 'GET_API_Jobs' : 'GET_HTML_Home' },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'body received': (r) => r.body && r.body.length > 0,
  });

  // Random user think time between 500ms and 1500ms
  sleep(0.5 + Math.random());
}
