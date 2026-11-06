// Browser-level guard for synthetic fixtures. This is not an OS network sandbox:
// Playwright APIRequestContext and background Chromium traffic are separate.
export async function restrictBrowserNetwork(context, base) {
  const allowed = new URL(base);
  if (allowed.protocol !== 'http:' || allowed.hostname !== '127.0.0.1' || !allowed.port)
    throw new Error('A dedicated loopback origin is required');

  // HTTP routing does not intercept WebSocket upgrades.
  await context.routeWebSocket('**/*', socket => socket.close({code: 1008, reason: 'Synthetic test only'}));
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (['data:', 'blob:'].includes(url.protocol)) return route.continue();
    if (url.origin !== allowed.origin) return route.abort();

    // route.continue() only intercepts the first URL in a redirect chain.
    // Fetch without following redirects, and reject every redirect before it
    // reaches Chromium. No browser fixture needs redirects to succeed.
    const response = await route.fetch({maxRedirects: 0});
    if (response.status() >= 300 && response.status() < 400) return route.abort();
    return route.fulfill({response});
  });
}
