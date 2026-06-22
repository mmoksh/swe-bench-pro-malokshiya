# google-play-scraper Incremental Review Sync

## Description

This task requires implementing an incremental review synchronization system for the google-play-scraper Node.js library. The ReviewSync class accepts a fetcher function and provides a `sync(appId, checkpoint?)` method that fetches all reviews on first run, then only new reviews on subsequent runs using a timestamp-based checkpoint. It must handle paginated responses via tokens, deduplicate reviews by ID across pages, stop early when previously-seen data (at or below the checkpoint timestamp) is reached, return reviews sorted by timestamp descending, and produce an updated checkpoint. The solution is ~47 lines in a new `lib/infra/reviewSync.js` file plus a 2-line wiring change to `index.js`. A naive approach fails because deduplication must work across pagination boundaries, early stopping must compare against the checkpoint timestamp (not ID), and the returned checkpoint must be the maximum timestamp across all collected reviews.

## Completion Rates

| Model | Trials | Pass | Fail | Rate |
|-------|--------|------|------|------|
| Oracle | 3 | - | - | -% |
| Opus 4.6 | 5 | - | - | -% |
| Sonnet 4.6 | 5 | - | - | -% |
| Avocado | 5 | - | - | -% |

> **Note:** Completion rates will be filled after running calibration trials.

## Model Analysis

Pending calibration runs.

## Anti-Cheating Analysis

- **Hardcoded outputs**: Tests use mock fetchers with synthetic review data and assert on structural properties (array length, checkpoint string value, ordering invariant, ID uniqueness). No hardcoded output strings.
- **Overfitting to visible tests**: The `pass_to_pass` test verifies existing gplay methods remain exported — orthogonal to ReviewSync.
- **Modifying test files**: The `test_patch` is applied by the verifier via `config.json`, not by the agent.
- **Bypassing the intended solution path**: Tests dynamically import from `../lib/infra/reviewSync.js` and construct ReviewSync with custom fetcher functions. The agent must implement the pagination loop, dedup, checkpoint comparison, and sorting logic — there's no shortcut.
