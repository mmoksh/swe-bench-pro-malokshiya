# Incremental Review Synchronization
We need to extend the Google Play Scrapper library (https://github.com/facundoolano/google-play-scraper) to support incremental review. Given an app ID, and a checkpoint, the library should return a list of reviews since the checkpoint.
Your task is to implement efficient incremental fetching of reviews.

## Requirements
* Currently, the `reviews` allows fetching a specific number of reviews given the app ID. We need to extend this to support incremental fetching. E.g. given an app ID and a checkpoint (review ID), the library should return a list of reviews since the checkpoint. The checkpoint should not be included in the returned list.
* Note that this is different from the `nextPaginationToken`. The `nextPaginationToken` is used to fetch the next page of reviews, while the checkpoint is used to fetch reviews since a specific review.
* The implementation must stop fetching additional pages as soon as it can determine that no further reviews need to be returned.

Example:
```
gplay.reviews({
  appId: 'com.dxco.pandavszombies',
  sort: gplay.sort.NEWEST,
  num: 1000,
  checkpoint: '12345'
}).then(console.log, console.log);

```
This should return a list of reviews since the checkpoint '12345', up to 1000 reviews. If the checkpoint 12345 is found at the 300th review, the library should return the reviews from 1st to 299th.

* The response should include the next checkpoint, so that the client can continue fetching reviews from the next checkpoint. Example:
```
{
  data: [...],
  nextCheckpoint: 'NEXT_CHECKPOINT'
}
```

1. Only include nextCheckpoint when checkpoint is provided; otherwise the field must be absent
2. nextCheckpoint = the id of the newest review returned (first element of data)
3. nextCheckpoint = null when no reviews are returned
