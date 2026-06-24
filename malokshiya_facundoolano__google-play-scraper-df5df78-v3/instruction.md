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

scraper.app({appId: 'com.google.android.apps.translate'})
  .then(console.log, console.log);
```

## Assumptions
* Assume each proxy is a web server that accepts HTTP requests, and it returns a JSON object with the following structure:
```json
{
  "proxy": "http://proxy1",
  "url": "https://play.google.com/store/apps/details?id=com.google.android.apps.translate",
  "data": {}
}
```
Where `proxy` is the URL of the proxy that processed the request, `url` is the URL of the Google Play API, and `data` is the response from the Google Play API.

## Requirements
When a list of proxies is provided, the scraper should send the requests through the proxies, not directly to Google Play. The current scrapper API should still return the same response as before, but the response should be fetched from the proxy, not directly from Google Play, unless no proxies are provided, in that case, the scraper should fall back to the original behavior.

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
* HTTP error responses (e.g., 404, 500) from a proxy are NOT proxy failures — the proxy successfully forwarded the upstream response. Do not retry or count these against the proxy's failure counter.

Each proxy must maintain an independent failure counter.
### Proxy Disabling
* When a proxy reaches `maxFailures`, it must be removed from the active rotation.
* Disabled proxies must not be selected for new requests until they recover.

### Cooldown Recovery
* A disabled proxy remains unavailable for `cooldownMs`.
* After the cooldown period expires, the proxy automatically becomes eligible for selection again.
* The proxy's failure counter should be reset when it re-enters rotation.

### Retry Behavior
If a request fails because of a proxy failure:
* Retry the request using a different healthy proxy.
* Do not retry the same proxy during the same request.
* Stop retrying once all currently healthy proxies have been attempted.

### Metrics
Expose runtime statistics for monitoring and debugging:

```ts
scraper.getMetrics();
```
Output:
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
      state: "cooldown",
      resumeTime: 1680000000
    }
  ]
}
```
