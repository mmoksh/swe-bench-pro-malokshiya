# Investigate and Fix `INT()` Formula on PostgreSQL
There is a bug in the formula engine where the `INT()` function does not work on PostgreSQL.

## Problem
Formula columns that use `INT()` fail completely when NocoDB is backed by PostgreSQL.

Examples that should work but currently fail include:

```text
INT(1)
INT(1.9)
INT({Price})
```

This issue is specific to PostgreSQL.

## Expected behavior
`INT()` should return the integer portion of the input value, consistent with the behavior on the other supported databases.

For example:
| Expression     | Expected Result                                   |
| -------------- | ------------------------------------------------- |
| `INT(1)`       | `1`                                               |
| `INT(1.9)`     | `1`                                               |
| `INT(-1.9)`    | `-1`                                              |
| `INT({Price})` | Integer value of the column                       |

## Observations
* The same formulas work correctly on MySQL and SQLite.
* Other numeric formula functions, including `FLOAT()`, `ROUND()`, and `STRING()`, work correctly on PostgreSQL.
* The failure is independent of the input data—it occurs even with constant literals.
* Existing projects migrated from SQLite to PostgreSQL experience broken `INT()` formulas without requiring any schema changes.

## Investigation
Identify why `INT()` is implemented differently for PostgreSQL.

In particular:
* Locate the implementation of the `INT()` formula across the supported database dialects.
* Compare the PostgreSQL implementation with the MySQL and SQLite implementations.
* Determine where the generated SQL diverges.

Do not assume the bug is limited to a single file. Trace the full compilation path from formula parsing through SQL generation until the final PostgreSQL query.

## Requirements
* Fix the PostgreSQL implementation so that `INT()` behaves consistently with MySQL and SQLite.
* Preserve the existing behavior of the other database backends.
* Avoid introducing database-specific regressions.
