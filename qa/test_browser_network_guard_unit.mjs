// Deterministic failure cases supplement the actual-Chrome network guard test.
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {restrictBrowserNetwork, closeRestrictedBrowserContext} from './browser_network_guard.mjs';

const origin = 'http://127.0.0.1:1234';
const never = () => new Promise(() => {});
const deferred = () => {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return {promise, resolve};
};
function context(overrides = {}) {
  return {
    closed: false,
    async routeWebSocket() {},
    async route(_pattern, handler) { this.handler = handler; },
    async setOffline() {},
    async unrouteAll() {},
    async close() { this.closed = true; },
    ...overrides,
  };
}
const route = overrides => ({
  request: () => ({url: () => `${origin}/fixture`, method: () => 'GET'}),
  async abort() {},
  ...overrides,
});

test('new requests during cleanup are aborted, existing handler drains first', async () => {
  let active = false, offline = false;
  const c = context({async setOffline() { assert.equal(active, false); offline = true; }});
  await restrictBrowserNetwork(c, origin, {closeTimeoutMs: 1000});
  const gate = deferred();
  const started = deferred();
  const existing = c.handler(route({
    async fetch() { active = true; started.resolve(); await gate.promise; active = false; return {status: () => 200}; },
    async fulfill() {},
  }));
  await started.promise;
  const closing = closeRestrictedBrowserContext(c);
  let aborted = 0;
  await Promise.all(Array.from({length: 100}, () => c.handler(route({
    async fetch() { assert.fail('new fetch must not run during close'); },
    async abort() { aborted++; },
  }))));
  assert.equal(aborted, 100);
  assert.equal(c.closed, false);
  assert.equal(offline, false);
  gate.resolve();
  await Promise.all([existing, closing]);
  assert.equal(offline, true);
  assert.equal(c.closed, true);
});

test('routes arriving while going offline are aborted and drained before unroute', async () => {
  const offlineEntered = deferred(), finishOffline = deferred(), finishAbort = deferred();
  let removed = false;
  const c = context({
    async setOffline() { offlineEntered.resolve(); await finishOffline.promise; },
    async unrouteAll() { removed = true; },
  });
  await restrictBrowserNetwork(c, origin, {closeTimeoutMs: 1000});
  const closing = closeRestrictedBrowserContext(c);
  await offlineEntered.promise;
  const blocked = c.handler(route({
    async fetch() { assert.fail('closing guard must not fetch'); },
    async abort() { await finishAbort.promise; },
  }));
  finishOffline.resolve();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(removed, false);
  finishAbort.resolve();
  await Promise.all([blocked, closing]);
  assert.equal(removed, true);
  assert.equal(c.closed, true);
});

test('synthetic interruption only aborts loopback requests and never bypasses origin checks', async () => {
  const c = context();
  let hookCalls = 0, aborted = 0, fetched = 0, fulfilled = 0;
  await restrictBrowserNetwork(c, origin, {abortRequest: () => ++hookCalls === 1});
  await c.handler(route({
    request: () => ({url: () => 'https://foreign.invalid/fixture', method: () => 'GET'}),
    async abort() { aborted++; },
    async fetch() { assert.fail('foreign origin must never be fetched'); },
  }));
  assert.equal(hookCalls, 0);
  await c.handler(route({
    async abort() { aborted++; },
    async fetch() { assert.fail('interrupted request must not be fetched'); },
  }));
  await c.handler(route({
    async fetch() { fetched++; return {status: () => 200}; },
    async fulfill() { fulfilled++; },
  }));
  assert.equal(hookCalls, 2);
  assert.equal(aborted, 2);
  assert.equal(fetched, 1);
  assert.equal(fulfilled, 1);
  await closeRestrictedBrowserContext(c);
});

test('response observer sees only successful loopback fetches before fulfilment', async () => {
  const c = context();
  const events = [];
  await restrictBrowserNetwork(c, origin, {observeResponse: async (request, response) => {
    events.push(['observe',request.url(),response.status()]);
  }});
  await c.handler(route({
    request: () => ({url: () => 'https://foreign.invalid/fixture', method: () => 'GET'}),
    async fetch() { assert.fail('foreign origin must never be fetched'); },
  }));
  await c.handler(route({
    async fetch() { return {status: () => 302}; },
  }));
  await c.handler(route({
    async fetch() { return {status: () => 200}; },
    async fulfill() { events.push(['fulfil']); },
  }));
  assert.deepEqual(events,[['observe',`${origin}/fixture`,200],['fulfil']]);
  await closeRestrictedBrowserContext(c);
});

test('only loopback static font GETs get one bounded reset retry', async () => {
  const c = context();
  await restrictBrowserNetwork(c, origin);
  for (const [path, method, expected] of [
    ['/assets/fonts/test.ttf', 'GET', 1],
    ['/assets/fonts/test.woff2', 'GET', 1],
    ['/api/fonts/test.ttf', 'GET', 0],
    ['/assets/fonts/test.ttf', 'POST', 0],
    ['/assets/script.js', 'GET', 0],
  ]) {
    await c.handler(route({
      request: () => ({url: () => origin + path, method: () => method}),
      async fetch(options) {
        assert.equal(options.maxRedirects, 0);
        assert.equal(options.maxRetries, expected);
        return {status: () => 200};
      },
      async fulfill() {},
    }));
  }
  await closeRestrictedBrowserContext(c);
});

test('response observer errors fail closed', async () => {
  const c = context();
  let aborted = false;
  await restrictBrowserNetwork(c, origin, {observeResponse: () => { throw new Error('observer failed'); }});
  await c.handler(route({
    async fetch() { return {status: () => 200}; },
    async fulfill() { assert.fail('failed observation must not be fulfilled'); },
    async abort() { aborted = true; },
  }));
  assert(aborted);
  await assert.rejects(closeRestrictedBrowserContext(c), /Synthetic browser network guard failed/);
});

test('an invalid synthetic interruption decision fails closed', async () => {
  const c = context();
  let aborted = 0;
  await restrictBrowserNetwork(c, origin, {abortRequest: () => 'not-a-boolean'});
  await c.handler(route({
    async abort() { aborted++; },
    async fetch() { assert.fail('invalid interruption decision must not fetch'); },
  }));
  assert.equal(aborted, 1);
  await assert.rejects(closeRestrictedBrowserContext(c), error => {
    assert(error instanceof AggregateError);
    assert.match(error.errors[0].message, /decision must be a boolean/);
    return true;
  });
});

test('a stuck handler fails within the deadline and still closes context', async () => {
  const c = context();
  await restrictBrowserNetwork(c, origin, {closeTimeoutMs: 30});
  void c.handler(route({fetch: never}));
  await assert.rejects(closeRestrictedBrowserContext(c), /Draining browser routes timed out/);
  assert.equal(c.closed, true);
});

test('removing routes and closing context are each bounded and both errors survive', async () => {
  const c = context({unrouteAll: never, close: never});
  await restrictBrowserNetwork(c, origin, {closeTimeoutMs: 30});
  await assert.rejects(closeRestrictedBrowserContext(c), error => {
    assert(error instanceof AggregateError);
    assert.match(error.errors[0].message, /Removing browser routes timed out/);
    assert.match(error.errors[1].message, /Closing browser context timed out/);
    return true;
  });
});

test('handler failures are recorded and cause cleanup to fail', async () => {
  const c = context();
  await restrictBrowserNetwork(c, origin, {closeTimeoutMs: 1000});
  await c.handler(route({request() { throw new Error('fixture request failure'); }, async abort() { throw new Error('already closed'); }}));
  await assert.rejects(closeRestrictedBrowserContext(c), error => {
    assert(error instanceof AggregateError);
    assert.match(error.errors[0].message, /fixture request failure/);
    return true;
  });
  assert.equal(c.closed, true);
});


test('failure to go offline fails closed and attempts to close context', async () => {
  let unroute = false;
  const c = context({setOffline: never, async unrouteAll() { unroute = true; }});
  await restrictBrowserNetwork(c, origin, {closeTimeoutMs: 30});
  await assert.rejects(closeRestrictedBrowserContext(c), /Taking browser offline timed out/);
  assert.equal(unroute, false);
  assert.equal(c.closed, true);
});
