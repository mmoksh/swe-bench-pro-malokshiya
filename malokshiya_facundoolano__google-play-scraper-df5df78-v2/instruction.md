# Proxy Pool and Rotation Support for Google Play Scraper
This module manages a pool of HTTP/HTTPS proxies used by the scraper.
The goal is to distribute requests across proxies, handle failures gracefully, and recover proxies when they become usable again.

## What this should do
At a high level, the proxy pool should:
- Keep a list of available proxies
- Rotate proxies for outgoing requests
- Spread traffic evenly across healthy proxies
- Detect failing proxies automatically
- Temporarily disable bad proxies
- Re-enable proxies after a cooldown period
- Work correctly under concurrent load

## API
```
class ProxyPool {
  add(proxy: ProxyConfig): void;
  getProxy(): ProxyConfig;
  reportSuccess(proxy: ProxyConfig): void;
  reportFailure(proxy: ProxyConfig): void;
}
```

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
