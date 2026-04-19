const baseUrl = process.env.WAOS_FRONTEND_BASE_URL || process.env.NEXT_PUBLIC_APP_URL || 'http://127.0.0.1:3000';
const optionalStaticPath = process.env.WAOS_DELIVERY_STATIC_PATH || '';
const checks = [
  { path: '/', expectCacheIncludes: 'no-store', requireVary: false },
  ...(optionalStaticPath ? [{ path: optionalStaticPath, expectCacheIncludes: 'max-age', requireVary: true }] : []),
];

async function check(path, expectCacheIncludes, requireVary) {
  const res = await fetch(new URL(path, baseUrl), {
    headers: { 'accept-encoding': 'gzip, br' },
  });
  const cache = res.headers.get('cache-control') || '';
  const vary = res.headers.get('vary') || '';
  if (!cache.toLowerCase().includes(expectCacheIncludes.toLowerCase())) {
    throw new Error(`${path} missing expected cache policy: ${expectCacheIncludes}; got ${cache}`);
  }
  if (requireVary && !vary.toLowerCase().includes('accept-encoding')) {
    throw new Error(`${path} missing Vary: Accept-Encoding; got ${vary}`);
  }
}

for (const item of checks) {
  await check(item.path, item.expectCacheIncludes, item.requireVary);
}

console.log(JSON.stringify({ ok: true, baseUrl, checks: checks.map((item) => item.path) }, null, 2));
