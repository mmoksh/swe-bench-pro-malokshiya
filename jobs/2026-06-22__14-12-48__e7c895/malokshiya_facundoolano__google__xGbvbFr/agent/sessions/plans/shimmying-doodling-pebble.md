# Plan: Proxy Pool and Rotation Support

## Context

The google-play-scraper makes all HTTP requests through a single module (`lib/utils/request.js`) using `got`. There is no proxy support. The goal is to add a `ProxyPool` class that rotates proxies, detects failures with exponential backoff, and recovers healthy proxies — then integrate it into the existing request pipeline so users can pass a proxy pool via `requestOptions`.

## Files to Create

### `lib/utils/proxyPool.js` — The ProxyPool class

**ProxyConfig shape:**
```js
{ host, port, protocol, auth?: { username, password } }
```

**Internal state per proxy:**
- `healthy` (boolean)
- `failCount` (consecutive failures)
- `disabledUntil` (timestamp when proxy can be retried)

**Methods:**
- `constructor(options)` — accepts `{ maxFailures = 5, baseBackoff = 1000, maxBackoff = 60000 }` with sensible defaults
- `add(proxy)` — adds a proxy to the pool
- `getProxy()` — returns the next healthy proxy via round-robin; also re-enables proxies whose cooldown has expired; throws if no proxies available
- `reportSuccess(proxy)` — resets fail count, marks healthy
- `reportFailure(proxy)` — increments fail count; if >= `maxFailures`, marks unhealthy with `disabledUntil = now + backoff` (exponential: `baseBackoff * 2^(failRound - 1)`, capped at `maxBackoff`)
- `getUrl(proxy)` — helper that builds `protocol://[auth@]host:port` URL string

**Round-robin:** Maintain an index; `getProxy()` scans from current index looking for a healthy (or cooldown-expired) proxy. Wraps around. Returns `null` if all disabled.

### `test/utils.proxyPool.js` — Unit tests

Pure unit tests (no network), testing:
- Adding proxies and round-robin rotation
- Failure counting and disabling after N failures
- Cooldown expiry and re-enabling
- Exponential backoff capping
- `getProxy()` returns `null` when all proxies disabled
- `reportSuccess` resets failure state

## Files to Modify

### `lib/utils/request.js` — Integrate proxy selection

Modify `doRequest` to accept and use a proxy pool:
- If `opts.proxyPool` is present, call `opts.proxyPool.getProxy()` to get a proxy
- Set `opts.agent` with an HTTPS/HTTP agent pointing at that proxy (using `got`'s native proxy support via the URL-based approach, or the simpler `prefixUrl` pattern — but since `got` v11 doesn't have built-in proxy, we'll use the `opts` to set the proxy URL on the request)
- Actually, the cleanest approach: since `got` v11 supports a custom `agent` option, but that requires `tunnel` or `hpagent` — instead, we can use `got`'s `hooks` or wrap the request. **Simpler approach:** Convert proxy to a URL and use `got`'s built-in options. But `got` v11 actually does NOT support proxies natively.

**Revised approach:** Rather than adding a proxy agent dependency, the integration will:
1. Accept `proxyPool` in the scraper options (alongside `requestOptions`, `throttle`)
2. In `request.js`, when a `proxyPool` is provided:
   - Call `proxyPool.getProxy()` to get a proxy config
   - Build the proxy URL and pass it through `got`'s `agent` option using Node's built-in `http.Agent` / `https.Agent` — actually this won't work for proxying.

**Final approach (no new dependencies):** The `ProxyPool` is a standalone utility. Integration with `got` requires the user to supply their own agent (e.g. `hpagent`, `tunnel`). The `request.js` integration:
1. Accepts `proxyPool` in opts
2. Calls `pool.getProxy()` before each request
3. Calls `pool.reportSuccess(proxy)` / `pool.reportFailure(proxy)` based on result
4. The user is responsible for setting up `requestOptions.agent` or the ProxyPool's `getUrl()` can be used with a proxy agent library of their choice

**Actually, the cleanest integration that works without new deps:** The `ProxyPool` just manages proxy state and rotation. `request.js` calls `getProxy()`, builds a proxy URL, and sets `got` options that work:
- For `got` v11, we can use the `https.request` built-in with the `HTTPS_PROXY` env approach — no, that's not per-request.

**Simplest correct approach:** Add the proxy URL to `got` request options. `got` v11 doesn't natively support proxies but the options get passed through. The user needs a proxy agent. Let's keep the `ProxyPool` as a standalone data structure and integrate it lightly:

In `request.js`:
- Extract `proxyPool` from opts (so it doesn't get passed to `got`)
- If present, get proxy via `getProxy()`, build URL, store reference
- Wrap the actual request in try/catch to call `reportSuccess`/`reportFailure`
- Let the proxy URL be available for users who configure their own agent

**Final decision:** Keep it simple. The ProxyPool is a standalone class. `request.js` integration:
1. If `opts.proxyPool` exists, call `getProxy()` and store the proxy reference
2. Set `opts.url` to route through the proxy (for HTTP proxies, this means setting the full URL as target and the proxy as the connection endpoint — but this doesn't work with `got` without an agent)

**OK, let me step back.** The requirement says "Proxy Pool and Rotation Support" — it's a utility class. The integration with `got` is a separate concern that depends on the user's setup. The deliverable is:

1. **`lib/utils/proxyPool.js`** — standalone `ProxyPool` class with the specified API
2. **`test/utils.proxyPool.js`** — comprehensive unit tests
3. **`lib/utils/request.js`** — light integration: extract `proxyPool` from opts, call `getProxy()` before requests, call `reportSuccess`/`reportFailure` after, and pass the proxy URL to got's options (users who need HTTPS proxying can pass `requestOptions.agent`)
4. **`index.js`** — export `ProxyPool` so users can create instances

## Detailed Implementation

### `lib/utils/proxyPool.js`

```js
class ProxyPool {
  constructor(options = {}) {
    this.proxies = [];  // array of { config, healthy, failCount, disabledUntil, failRound }
    this.currentIndex = 0;
    this.maxFailures = options.maxFailures || 5;
    this.baseBackoff = options.baseBackoff || 1000;
    this.maxBackoff = options.maxBackoff || 60000;
  }

  add(proxy) { ... }
  getProxy() { ... }      // round-robin, skips disabled, re-enables expired cooldowns
  reportSuccess(proxy) { ... }
  reportFailure(proxy) { ... }
  getUrl(proxy) { ... }   // builds protocol://user:pass@host:port
}
```

### `lib/utils/request.js` changes

- Accept `proxyPool` from opts (delete from opts before passing to `got`)
- Before request: `const proxy = opts.proxyPool?.getProxy()`
- After success: `proxyPool.reportSuccess(proxy)`
- After failure: `proxyPool.reportFailure(proxy)`, then rethrow

### `index.js` changes

- Import and re-export `ProxyPool`

### `test/utils.proxyPool.js`

- Test round-robin ordering
- Test failure threshold and disable behavior
- Test cooldown expiry re-enables proxy
- Test exponential backoff with cap
- Test all-proxies-disabled returns null
- Test reportSuccess resets state
- Test getUrl with and without auth

## Verification

1. Run `npm run lint` to check style compliance
2. Run `npm test` to verify existing tests still pass
3. Run `npx mocha test/utils.proxyPool.js --timeout 5000` for the new tests specifically
