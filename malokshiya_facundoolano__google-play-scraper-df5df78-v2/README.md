# google-play-scraper Proxy Pool

## Description

This task requires implementing a proxy pool and rotation subsystem for the google-play-scraper Node.js library. The ProxyPool class must maintain a pool of HTTP/HTTPS proxies, rotate them per request, track proxy health, temporarily disable failing proxies with cooldown, restore health on success, and ensure fair distribution across healthy proxies. The task tests several interacting behaviors (rotation, failure tracking, health recovery, fairness) that must all work correctly together.

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

- **Hardcoded outputs**: Tests use behavioral assertions (`assert.isTrue`, `assert.isAbove`, `assert.strictEqual`) against dynamic state (proxy rotation order, failure counts, fairness distribution). No literal strings to pattern-match.
- **Overfitting to visible tests**: The `pass_to_pass` test verifies that existing gplay methods (app, search, list, etc.) remain exported — a regression check orthogonal to the ProxyPool implementation.
- **Modifying test files**: The `test_patch` is applied by the verifier via `config.json`, not by the agent. The verifier resets to base commit and applies patches independently.
- **Bypassing the intended solution path**: Tests dynamically import from `../lib/infra/proxyPool.js` and test the class API (add, getProxy, reportSuccess, reportFailure, healthy, size). An agent must create a correctly-structured ESM module exporting a ProxyPool class with the specified behavior.
