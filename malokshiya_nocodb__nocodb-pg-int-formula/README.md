# NocoDB PostgreSQL INT() Formula Bug

## Description

The `INT()` formula function in NocoDB is completely broken on PostgreSQL deployments. When a user creates a formula column using `INT()` — for example `INT({Price})` or even `INT(1)` — the entire table view fails to load with a 500 error. The root cause is subtle: the PostgreSQL-specific function mapping in `packages/nocodb/src/db/functionMappings/pg.ts` doesn't properly handle the async contract of the `args.fn()` callback, which returns a `Promise`. Every sibling function in the same file (`FLOAT`, `ROUND`, `STRING`, `SEARCH`) correctly uses `async/await`, but `INT` does not. The unawaited Promise object is coerced to the string `[object Promise]` and interpolated into a `knex.raw()` SQL template, producing syntactically invalid SQL that PostgreSQL rejects.

A naive approach of simply changing the SQL generation strategy (e.g., switching to `CAST(... as INTEGER)`) won't work — the agent must recognize that the issue is the missing async/await pattern, not the SQL dialect. The fix requires understanding how NocoDB's formula query builder dispatches to per-database function mappings via the `MapFnArgs` interface, specifically that `fn()` returns `Promise<{builder: Knex.QueryBuilder}>`.

## Completion Rates

| Agent | Trials | Pass Rate |
|-------|--------|-----------|
| Oracle | 3/3 | 100% |
| Sonnet 4.6 | TBD | TBD |
| Opus 4.6 | TBD | TBD |
| Avocado | TBD | TBD |

## Model Analysis

TBD — to be filled after running model trials via `codimango bench run`.

**Expected failure modes:**
- Agent changes the SQL template (REGEXP_REPLACE → CAST) without adding async/await — tests still fail
- Agent fixes the async but breaks the regex pattern or SQL structure — PG-specific tests fail
- Agent modifies MySQL or SQLite implementations unnecessarily — regression tests fail
- Agent doesn't remove the `// todo: correction` comment — edge case test fails
- Agent uses `.then()` chaining instead of async/await — may pass but would be inconsistent with the codebase pattern

## Anti-Cheating Analysis

- **Hardcoded outputs:** Tests check SQL output dynamically (no string literals to hardcode). The `[object Promise]` check is a negative assertion — absence of the bad string, not presence of a specific good string.
- **Overfitting to visible tests:** `pass_to_pass` tests verify MySQL and SQLite INT() functions remain unchanged. An agent that over-edits the shared infrastructure or touches sibling files will break these regression tests.
- **Modifying test files:** Test patch is applied by the verifier, not the agent. The agent's patch is validated against the repo, not the test directory.
- **Bypassing the intended solution path:** Tests check both the code structure (async/await presence via static analysis) AND the runtime behavior (SQL output doesn't contain `[object Promise]`). An agent can't satisfy both by deleting the function or stubbing it out — it must produce a working async implementation that generates valid PostgreSQL SQL.
