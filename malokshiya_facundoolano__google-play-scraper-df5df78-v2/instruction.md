# Proxy Pool and Rotation Support for Google Play Scraper

Implement a proxy management subsystem used by the request executor.

## Requirements

The system must:

- Maintain a pool of proxies
- Support HTTP/HTTPS proxies
- Rotate proxies per request
- Track proxy health
- Temporarily disable failing proxies
- Re-enable proxies after a cooldown period
- Ensure fair distribution across healthy proxies

---

## API

```ts
interface ProxyConfig {
  url: string;
}
```

```ts
class ProxyPool {
  add(proxy: ProxyConfig): void;

  getProxy(): ProxyConfig;

  reportSuccess(proxy: ProxyConfig): void;

  reportFailure(proxy: ProxyConfig): void;
}
```

---

## Behavior Requirements

### Proxy Rotation Strategies (must support at least one)

- Round-robin (required baseline)
- Optional: random or least-used

### Failure Handling

- After N consecutive failures, proxy is temporarily disabled
- Disabled proxies are retried after a cooldown period
- Cooldown increases with repeated failures (exponential backoff allowed)

### Health Recovery

- Periodic re-validation of failed proxies
- Successful request restores proxy to healthy pool

### Fairness

- Avoid overusing a single proxy when multiple healthy proxies exist

### Concurrency Safety

- Must be safe under concurrent request load
- No race conditions in proxy selection or state updates
