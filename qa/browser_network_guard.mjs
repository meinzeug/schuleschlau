// Browser-level guard for synthetic fixtures. This is not an OS network sandbox:
// Playwright APIRequestContext and background Chromium traffic are separate.
const routeStates = new WeakMap();

function bounded(promise, milliseconds, description) {
  let timer;
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(`${description} timed out`)), milliseconds);
    }),
  ]).finally(() => clearTimeout(timer));
}

export async function restrictBrowserNetwork(context, base, {fetchTimeoutMs = 30000, closeTimeoutMs = 35000, abortRequest = null, observeResponse = null} = {}) {
  const allowed = new URL(base);
  if (allowed.protocol !== 'http:' || allowed.hostname !== '127.0.0.1' || !allowed.port)
    throw new Error('A dedicated loopback origin is required');
  if (!Number.isInteger(fetchTimeoutMs) || fetchTimeoutMs < 1 || fetchTimeoutMs > 30000)
    throw new Error('A bounded fetch timeout is required');
  if (!Number.isInteger(closeTimeoutMs) || closeTimeoutMs < 1 || closeTimeoutMs > 60000)
    throw new Error('A bounded close timeout is required');
  if (abortRequest !== null && typeof abortRequest !== 'function')
    throw new Error('The synthetic abort hook must be a function');
  if (observeResponse !== null && typeof observeResponse !== 'function')
    throw new Error('The synthetic response observer must be a function');

  // HTTP routing does not intercept WebSocket upgrades.
  await context.routeWebSocket('**/*', socket => socket.close({code: 1008, reason: 'Synthetic test only'}));
  const state = {failures: [], handlers: new Set(), closing: false, closeTimeoutMs};
  routeStates.set(context, state);
  await context.route('**/*', route => {
    const handled = handleRoute(route);
    state.handlers.add(handled);
    // Return the observed promise; don't create an unobserved .finally promise.
    return handled.finally(() => state.handlers.delete(handled));
  });
  async function handleRoute(route) {
    try {
      // Do not start additional requests after teardown starts, including to the
      // permitted origin. Existing fetches remain tracked and bounded.
      if (state.closing) return await route.abort();
      const url = new URL(route.request().url());
      if (['data:', 'blob:'].includes(url.protocol)) return await route.continue();
      if (url.origin !== allowed.origin) return await route.abort();
      // The test hook can only make loopback traffic fail; it never bypasses
      // the origin/redirect guard and does not install a competing route.
      const interrupted = abortRequest ? abortRequest(route.request()) : false;
      if (typeof interrupted !== 'boolean') throw new Error('Synthetic abort decision must be a boolean');
      if (interrupted) return await route.abort('failed');

      // route.continue() only intercepts the first URL in a redirect chain.
      // Fetch without following redirects, and reject every redirect before it
      // reaches Chromium. No browser fixture needs redirects to succeed.
      // A static font may hit a transient loopback ECONNRESET while Chromium
      // changes views. Retry only this read once; API calls and every write
      // remain single-attempt, and repeated failures still fail the test.
      const isStaticFont = route.request().method() === 'GET' &&
        url.pathname.startsWith('/assets/') && /\.(?:ttf|otf|woff2?)$/i.test(url.pathname);
      const response = await route.fetch({maxRedirects: 0, timeout: fetchTimeoutMs, maxRetries: isStaticFont ? 1 : 0});
      if (response.status() >= 300 && response.status() < 400) return await route.abort();
      if (observeResponse) await observeResponse(route.request(), response);
      return await route.fulfill({response});
    } catch (error) {
      state.failures.push(error);
      // Let the page finish its failed request; the recorded error causes the
      // test's close operation to fail even if its page assertions happened to pass.
      try { await route.abort('failed'); } catch { /* already disconnected */ }
    }
  }
}

// Stop browser traffic before removing routes; otherwise a request created
// while unrouteAll waits could escape the synthetic-only guard. Do not close
// the context until all existing route.fetch/fulfill handlers have finished.
export async function closeRestrictedBrowserContext(context) {
  if (!context) return;
  const state = routeStates.get(context);
  const timeout = state?.closeTimeoutMs ?? 35000;
  if (state) state.closing = true;
  let failure;
  try {
    // Keep routing installed while draining: closing=true blocks every new
    // request, while existing allowed fetches can finish without an offline
    // transition resetting their sockets. Never remove the guard on timeout.
    const drain = async () => {
      while (state?.handlers.size) await Promise.allSettled([...state.handlers]);
    };
    await bounded(drain(), timeout, 'Draining browser routes');
    await bounded(context.setOffline(true), timeout, 'Taking browser offline');
    // A request may have reached the guard between the first drain and the
    // offline transition. Finish its abort before removing routes.
    await bounded(drain(), timeout, 'Draining browser routes');
    await bounded(context.unrouteAll({behavior: 'wait'}), timeout, 'Removing browser routes');
    if (state?.failures.length) throw new AggregateError(state.failures, 'Synthetic browser network guard failed');
  } catch (error) {
    failure = error;
  }
  try {
    await bounded(context.close(), timeout, 'Closing browser context');
  } catch (error) {
    failure = failure ? new AggregateError([failure, error], 'Synthetic browser cleanup failed') : error;
  } finally {
    routeStates.delete(context);
  }
  if (failure) throw failure;
}
