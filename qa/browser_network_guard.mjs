// Browser-level guard for synthetic fixtures. This is not an OS network sandbox:
// Playwright APIRequestContext and background Chromium traffic are separate.
const routeFailures = new WeakMap();

export async function restrictBrowserNetwork(context, base, {fetchTimeoutMs = 30000} = {}) {
  const allowed = new URL(base);
  if (allowed.protocol !== 'http:' || allowed.hostname !== '127.0.0.1' || !allowed.port)
    throw new Error('A dedicated loopback origin is required');
  if (!Number.isInteger(fetchTimeoutMs) || fetchTimeoutMs < 1 || fetchTimeoutMs > 30000)
    throw new Error('A bounded fetch timeout is required');

  // HTTP routing does not intercept WebSocket upgrades.
  await context.routeWebSocket('**/*', socket => socket.close({code: 1008, reason: 'Synthetic test only'}));
  const failures = [];
  routeFailures.set(context, failures);
  await context.route('**/*', async route => {
    try {
      const url = new URL(route.request().url());
      if (['data:', 'blob:'].includes(url.protocol)) return await route.continue();
      if (url.origin !== allowed.origin) return await route.abort();

    // route.continue() only intercepts the first URL in a redirect chain.
    // Fetch without following redirects, and reject every redirect before it
    // reaches Chromium. No browser fixture needs redirects to succeed.
      const response = await route.fetch({maxRedirects: 0, timeout: fetchTimeoutMs});
      if (response.status() >= 300 && response.status() < 400) return await route.abort();
      return await route.fulfill({response});
    } catch (error) {
      failures.push(error);
      // Let the page finish its failed request; the recorded error causes the
      // test's close operation to fail even if its page assertions happened to pass.
      try { await route.abort('failed'); } catch { /* already disconnected */ }
    }
  });
}

// Stop browser traffic before removing routes; otherwise a request created
// while unrouteAll waits could escape the synthetic-only guard. Do not close
// the context until all existing route.fetch/fulfill handlers have finished.
export async function closeRestrictedBrowserContext(context) {
  if (!context) return;
  try {
    await context.setOffline(true);
    await context.unrouteAll({behavior: 'wait'});
    const failures = routeFailures.get(context) || [];
    if (failures.length) throw new AggregateError(failures, 'Synthetic browser network guard failed');
  } finally {
    routeFailures.delete(context);
    await context.close();
  }
}
