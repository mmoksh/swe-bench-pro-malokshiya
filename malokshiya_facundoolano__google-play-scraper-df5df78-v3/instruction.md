# Proxy Pool and Rotation Support for Google Play Scraper
Implement a proxy management subsystem for the Google Play Scraper library. The subsystem should be integrated into the request execution pipeline and allow requests to be routed through a pool of proxies.

## Public API
The scraper should support the following configuration:
```ts
const scraper = createScraper({
  proxyPool: {
    proxies: [
      {
        id: "us-east-1",
        url: "http://proxy1"
      },
      {
        id: "us-west-1",
        url: "http://proxy2"
      }
    ],

    maxFailures: 3,
    cooldownMs: 300000
  }
});
```

## Requirements
### Proxy Rotation
* Maintain a pool of configured proxies.
* Distribute requests evenly across all healthy proxies.
* Exclude disabled proxies from selection.
* Automatically include recovered proxies back into rotation.

### Failure Tracking
A request should be considered failed when:
* The connection to the proxy cannot be established.
* The request times out.
* The proxy returns a transport-level error.

Each proxy must maintain an independent failure counter.
### Proxy Disabling
* When a proxy reaches `maxFailures`, it must be removed from the active rotation.
* Disabled proxies must not be selected for new requests.

### Cooldown Recovery
* A disabled proxy remains unavailable for `cooldownMs`.
* After the cooldown period expires, the proxy automatically becomes eligible for selection again.
* The proxy's failure counter should be reset when it re-enters rotation.

### Retry Behavior
If a request fails because of a proxy failure:
* Retry the request using a different healthy proxy.
* Do not retry the same proxy during the same request.
* Stop retrying once all currently healthy proxies have been attempted.
* Surface the failure to the caller if no healthy proxies remain.

### Concurrency
The proxy pool must operate correctly when multiple requests are executed concurrently.

### Metrics
Expose runtime statistics for monitoring and debugging:
```ts
{
  proxies: [
    {
      id: "us-east-1",
      requests: 1245,
      failures: 12,
      state: "healthy"
    },
    {
      id: "us-west-1",
      requests: 1187,
      failures: 4,
      state: "cooldown"
    }
  ]
}
```

## Deliverables
* Proxy pool implementation.
* Integration with the existing request execution pipeline.
* Unit tests covering rotation, failure handling, cooldown recovery, retries, and concurrent request scenarios.
