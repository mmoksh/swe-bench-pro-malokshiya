# Incremental Review Synchronization
Your task is to implement efficient incremental fetching of reviews.

## Requirements

```
interface Review {
  id: string;
  timestamp: number;
}
```

```
class ReviewSync {
  sync(appId: string, checkpoint?: string): Promise<reviews: Review[], checkpoint: string>;
  new ReviewSync(fetcher);
}
```

* The constructor takes a fetcher function (appId, token) → {reviews, token}

## Behavior
- First run fetches all reviews
- Subsequent runs fetch only new reviews since checkpoint
- Stops early when previously-seen data is reached
- Returns updated checkpoint
- Must handle duplicates and out-of-order pagination
