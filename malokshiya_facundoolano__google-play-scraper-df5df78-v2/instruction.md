# Marketplace Scraper Infrastructure (Advanced SDK Design)

Design and implement core infrastructure for a Node.js SDK that interacts with a remote marketplace API (search, app details, reviews, developer data). The system must be production-grade and resilient to rate limits, failures, and large-scale scraping workloads.

---

# 1. Request Execution Framework (Rate Limiting + Retry)

Implement a centralized request execution layer.

## Requirements

- Global concurrency limit across all requests
- Configurable rate limiting (fixed or sliding window)
- Retry with exponential backoff
- Retry jitter to avoid thundering herd
- Configurable retry conditions (e.g., HTTP status, error type)
- Timeout handling per request

## API

```ts
interface RetryOptions {
  attempts: number;
  initialDelayMs: number;
  maxDelayMs: number;
  jitter: boolean;
}

interface RequestOptions {
  timeoutMs?: number;
  retry?: RetryOptions;
}
```

```ts
class RequestExecutor {
  execute<T>(
    fn: () => Promise<T>,
    options?: RequestOptions
  ): Promise<T>;
}
```

---

# 2. Proxy Pool and Rotation Support

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

---

# 3. Structured Diagnostics and Error Reporting

Replace raw errors with structured diagnostics.

## Requirements

```ts
interface Diagnostic {
  code: string;
  path: string;
  message: string;
  severity: "warning" | "error";
}
```

```ts
class ParseError extends Error {
  diagnostics: Diagnostic[];
}
```

## Behavior

- Collect multiple errors per response
- Preserve partial parsing results when possible
- Provide machine-readable error context for logging/monitoring

---

# 4. Incremental Review Synchronization

Implement efficient incremental fetching of reviews.

## Requirements

```ts
interface Review {
  id: string;
  timestamp: number;
}
```

```ts
class ReviewSync {
  sync(appId: string, checkpoint?: string): Promise<Review[]>;
}
```

## Behavior

- First run fetches all reviews
- Subsequent runs fetch only new reviews since checkpoint
- Stops early when previously-seen data is reached
- Returns updated checkpoint
- Must handle duplicates and out-of-order pagination

---

# 5. TypeScript SDK Modernization

Refactor SDK into strongly typed TypeScript APIs.

## Requirements

- Strict typing across all public APIs
- Discriminated unions for responses
- Fully exported interfaces
- Backward compatible runtime behavior

## Core Types

```ts
interface AppDetails {}
interface Review {}
interface Developer {}
interface SearchResult {}
```

---

# 6. Developer Catalog APIs

Implement developer-related endpoints.

## APIs

```ts
searchDeveloper(name: string)
developerInfo(developerId: string)
developerApps(developerId: string)
```

## Requirements

- Handle pagination
- Deduplicate results
- Preserve partial results on failure
- Efficient for large developer catalogs

---

# 7. Application Change Tracking System

Track changes in marketplace app metadata over time.

## Data Model

```ts
interface AppSnapshot {
  version: string;
  rating: number;
  installs: string;
  price: string;
}
```

## Implementation

```ts
class ChangeTracker {
  update(appId: string, snapshot: AppSnapshot): ChangeSet;
}
```

## Requirements

- Detect changes in:
  - Version
  - Rating
  - Install count
  - Price
- Ignore duplicate snapshots
- Must scale to millions of tracked apps
- Keep memory usage bounded

---

# Deliverables

For all sections:

- Production-ready implementation
- Unit tests
- Complexity analysis
- Design decisions write-up
- Notes on scalability and failure handling
