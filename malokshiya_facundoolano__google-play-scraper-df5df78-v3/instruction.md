# Incremental Review Synchronization

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
  sync(appId: string, checkpoint?: string): Promise<reviews: Review[], checkpoint: string>;
}
```

## Behavior

- First run fetches all reviews
- Subsequent runs fetch only new reviews since checkpoint
- Stops early when previously-seen data is reached
- Returns updated checkpoint
- Must handle duplicates and out-of-order pagination
