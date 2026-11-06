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
  request: () => ({url: () => `${origin}/fixture`}),
  async abort() {},
  ...overrides,
});

test('new requests during cleanup are aborted, existing handler drains first', async () => {
  const c = context();
  await restrictBrowserNetwork(c, origin, {closeTimeoutMs: 1000});
  const gate = deferred();
  const started = deferred();
  const existing = c.handler(route({
    async fetch() { started.resolve(); await gate.promise; return {status: () => 200}; },
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
  gate.resolve();
  await Promise.all([existing, closing]);
  assert.equal(c.closed, true);
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
