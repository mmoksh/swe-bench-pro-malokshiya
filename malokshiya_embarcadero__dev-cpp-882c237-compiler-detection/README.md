# Dev-Cpp Missing Compiler Detection

## Description

Dev-C++ 5.11 fails to detect installed GCC/MinGW compilers on systems with moderately long PATH environment variables. The root cause is a Unicode string handling bug in `Source/Utils.pas`: the `SetPath` procedure uses `SizeOf(OldPath)` instead of `Length(OldPath)` as the buffer size parameter to the Windows `GetEnvironmentVariable` API. In Delphi's Unicode builds, `Char` is `WideChar` (2 bytes), so `SizeOf` returns the byte count (4098) rather than the character count (2049). The API expects a character count, causing a buffer overflow that corrupts the PATH and prevents compiler discovery.

This task is non-trivial because the model must: (1) trace compiler detection through the codebase to find the `SetPath` procedure, (2) understand the Delphi/Pascal `SizeOf` vs `Length` distinction for static arrays of wide characters, and (3) recognize the mismatch with the Windows API's character-count expectation. A naive approach of expanding search paths in `FindSets` (which all models initially attempt) won't fix the underlying PATH corruption.

## Completion Rates

| Model | Agent | Trials | Pass Rate |
|-------|-------|--------|-----------|
| Oracle | oracle | 3/3 | 100% |
| Opus 4.6 | claude-code | 0/5 | 0% |
| Sonnet 4.6 | claude-code | 0/5 | 0% |
| Avocado | metacode | 1/5 | 20% |

## Model Analysis

**Opus 4.6 (0/5):** All 5 trials expanded `FindSets` in `devCFG.pas` to search additional MinGW locations (TDM-GCC-64, TDM-GCC-32, common system paths, PATH scanning). None identified the `SizeOf`/`Length` bug in `SetPath`.

**Sonnet 4.6 (0/5):** Same pattern as Opus — all trials focused on expanding compiler search paths rather than investigating PATH handling.

**Avocado (1/5):** 1 trial correctly identified and fixed the `SizeOf(OldPath)` → `Length(OldPath)` change. The 4 failures break down as:
- 3 trials: Did not find the SizeOf bug (same failure mode as Claude models)
- 1 trial: Found and fixed the SizeOf bug but restructured the buffer code (removed the static array), passing 5/6 tests

**Dominant failure mode (9/10 total failures):** Models correctly identify that compiler detection starts in `FindSets` but never trace through to `SetPath` where the PATH is assembled. They attempt to broaden the search by adding more paths to check, without realizing the existing PATH is being corrupted before it's searched.

These failures reflect reasoning gaps — the models fail to follow the chain: `FindSets` → compiler bin dir → `SetPath` → `GetEnvironmentVariable` → `SizeOf` bug. This is not a task-setup issue.

## Anti-Cheating Analysis

- **Hardcoded outputs**: Tests parse the actual Pascal source code and compile extracted expressions with Free Pascal Compiler — there are no string literals to hardcode. The FPC behavioral test evaluates the expression dynamically.
- **Overfitting to visible tests**: `pass_to_pass` tests verify procedure structure, string operations, and other GetEnvironmentVariable calls that the agent cannot predict from `fail_to_pass` tests alone.
- **Modifying test files**: Tests are mounted read-only at `/tests/` by the harness. The agent's patch is applied to `/app/` (the Dev-Cpp repo), not the test directory.
- **Bypassing the intended solution path**: The FPC compilation test extracts the actual buffer size expression from the source, compiles it in `{$mode delphiunicode}` (where `Char=WideChar`), and verifies the result equals the array element count. Simply removing or stubbing the function would fail the `test_setpath_procedure_exists` check.
