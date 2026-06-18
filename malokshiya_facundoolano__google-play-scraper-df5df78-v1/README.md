# google-play-scraper Search Fix

## Description

This task requires fixing the broken `search()` function in the [google-play-scraper](https://github.com/facundoolano/google-play-scraper) Node.js library. The search endpoint stopped returning results because Google Play changed both its URL structure and its embedded data format. The fix involves two coupled changes: correcting the URL path from `/work/search` to `/store/search?c=apps`, and updating the data extraction mappings throughout `lib/search.js` to match the new response structure (different `ds:` key, different array indices for app fields, dynamic section finding instead of hardcoded paths, and exact-match app handling). A naive approach of only fixing the URL still fails because the old data extraction paths return empty results against the new response format.

## Completion Rates

| Model | Trials | Pass | Fail | Rate |
|-------|--------|------|------|------|
| Oracle | 3 | 3 | 0 | 100% |
| Opus 4.6 | 5 | 5 | 0 | 100% |
| Sonnet 4.6 | 5 | 3 | 2 | 60% |
| Avocado | 5 | 2 | 3 | 40% |

## Model Analysis

### Opus 4.6 (5/5 passed)
All 5 trials succeeded. Opus consistently identified both the URL issue and the data mapping changes needed.

### Sonnet 4.6 (3/5 passed)
- **Trial dyM3Tcx (FAIL)**: Did not fix the URL path — still used `/work/search`. Nock rejected the request since only `/store/search` was mocked. The model failed to identify the root cause.
- **Trial y2yGcRu (FAIL)**: Fixed the URL to `/store/search` but used incorrect data extraction mappings. The response was retrieved but parsed to zero results.

### Avocado (2/5 passed)
- **Trials 2euY7dn, yHKYEKv (FAIL)**: Broke the data pipeline — produced `undefined` where Ramda's `R.map` expected an array (`Cannot read properties of undefined (reading 'fantasy-land/map')`). The model restructured the parsing logic incorrectly.
- **Trial hQe8Vxo (FAIL)**: Fixed the URL but used wrong data extraction paths. Results parsed to empty array.

### Failure Mode Summary

| Failure Mode | Count | Models |
|-------------|-------|--------|
| URL not fixed | 1 | Sonnet |
| URL fixed, mappings wrong (empty results) | 2 | Sonnet, Avocado |
| Data pipeline broken (runtime error) | 2 | Avocado |

All failures reflect reasoning gaps, not task-setup issues. The URL-only fix failure shows models can miss the coupling between URL and data format changes. The mapping failures show that reverse-engineering correct array indices from Google Play's deeply nested response structure is genuinely hard.

## Anti-Cheating Analysis

- **Hardcoded outputs**: Tests use `assert.isAbove(apps.length, 0)` and structural validation (type checks on `appId`, `title`, `score`, `free`) rather than comparing against literal values. A model cannot hardcode expected output strings.
- **Overfitting to visible tests**: The `pass_to_pass` validation tests (missing term, num > 250) verify unchanged behavior that doesn't depend on the fix. A model can't selectively break those paths to pass search tests.
- **Modifying test files**: The `test_patch` is applied by the verifier via `config.json`, not by the agent. The agent's patch is applied first, then the verifier resets and applies tests independently. The mock data structure in the test file is visible to the agent (as context for understanding the expected response format), but the agent cannot modify test assertions.
- **Bypassing the intended solution path**: Tests use nock to intercept HTTP at `/store/search` specifically. Any fix that doesn't use the correct URL path gets rejected by nock's `disableNetConnect()`. The mock response follows Google Play's actual `AF_initDataCallback` embedding pattern, so the model must use the real `scriptData.parse()` pipeline — not a shortcut.
