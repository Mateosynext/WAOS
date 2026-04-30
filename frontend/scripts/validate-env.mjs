const REQUIRED_PROD = [
  'NEXT_PUBLIC_API_BASE_URL',
  'API_INTERNAL_URL',
  'NEXT_PUBLIC_APP_URL',
];

function clean(value) {
  return String(value || '').trim().replace(/\/$/, '');
}

function isProductionLike() {
  return process.env.NODE_ENV === 'production' || process.env.VERCEL === '1' || process.env.APP_ENV === 'production';
}

function isHttps(url) {
  return /^https:\/\//i.test(url);
}

function validate() {
  const errors = [];
  const warnings = [];
  const prod = isProductionLike();
  for (const key of REQUIRED_PROD) {
    const value = clean(process.env[key]);
    if (!value) {
      if (prod) errors.push(`${key} is required for production builds.`);
      else warnings.push(`${key} is not set; dev fallbacks may be used locally.`);
      continue;
    }
    if (prod && !isHttps(value)) {
      errors.push(`${key} must use https in production.`);
    }
  }

  const publicApi = clean(process.env.NEXT_PUBLIC_API_BASE_URL);
  const internalApi = clean(process.env.API_INTERNAL_URL);
  const privateApi = clean(process.env.API_BASE_URL);
  const publicApp = clean(process.env.NEXT_PUBLIC_APP_URL || process.env.PUBLIC_APP_URL);

  if (prod && publicApi && internalApi && publicApi !== internalApi) {
    warnings.push('NEXT_PUBLIC_API_BASE_URL and API_INTERNAL_URL differ; confirm this is intentional for Vercel server-side fetches.');
  }
  if (prod && publicApi && privateApi && publicApi !== privateApi) {
    warnings.push('NEXT_PUBLIC_API_BASE_URL and API_BASE_URL differ; confirm proxy/routing is intentional.');
  }
  if (prod && publicApp && publicApi && publicApp === publicApi) {
    warnings.push('NEXT_PUBLIC_APP_URL should normally differ from NEXT_PUBLIC_API_BASE_URL.');
  }

  return { errors, warnings };
}

const { errors, warnings } = validate();
for (const line of warnings) console.warn(`[env:warn] ${line}`);
if (errors.length) {
  for (const line of errors) console.error(`[env:error] ${line}`);
  process.exit(1);
}
console.log('[env:ok] frontend env validation passed');

if (!process.exitCode) process.exit(0);
