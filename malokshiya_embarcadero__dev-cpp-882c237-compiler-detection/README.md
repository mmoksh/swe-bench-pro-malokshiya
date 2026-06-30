# Dev-Cpp Missing Compiler Detection

## Description

Dev-C++ 5.11 fails to detect installed GCC/MinGW compilers on systems with moderately long PATH environment variables. The root cause is a Unicode string handling bug in `Source/Utils.pas`: the `SetPath` procedure uses `SizeOf(OldPath)` instead of `Length(OldPath)` as the buffer size parameter to the Windows `GetEnvironmentVariable` API. In Delphi's Unicode builds, `Char` is `WideChar` (2 bytes), so `SizeOf` returns the byte count (4098) rather than the character count (2049). The API expects a character count, causing a buffer overflow that corrupts the PATH and prevents compiler discovery.

This task is non-trivial because the model must: (1) trace compiler detection through the codebase to find the `SetPath` procedure, (2) understand the Delphi/Pascal `SizeOf` vs `Length` distinction for static arrays of wide characters, and (3) recognize the mismatch with the Windows API's character-count expectation. A naive approach of expanding search paths in `FindSets` (which all Claude models attempt) won't fix the underlying PATH corruption.

## Completion Rates

| Model | Agent | Trials | Pass Rate |
|-------|-------|--------|-----------|
| Oracle | oracle | 3/3 | 100% |
| Opus 4.6 | claude-code | 5/10 | 50% |
| Sonnet 4.6 | claude-code | 6/10 | 60% |
| Avocado | metacode | 7/10 | 70% |

## Model Analysis

**Opus 4.6 (5/10):** High variance. When successful, Opus traces the bug to `SetPath` in `Utils.pas` and replaces the 3-arg `GetEnvironmentVariable` call with `SysUtils.GetEnvironmentVariable('PATH')`. When unsuccessful, Opus focuses on expanding `FindSets` search paths in `devCFG.pas` without investigating PATH reading.

**Sonnet 4.6 (6/10):** Similar variance. Successful trials find `SetPath` and apply the SysUtils wrapper or fix the buffer size. Failures focus on `devCFG.pas` search path expansion.

**Avocado (7/10):** Most consistent. Successful trials either change `SizeOf(OldPath)` → `Length(OldPath)` or use the `SysUtils.GetEnvironmentVariable('PATH')` wrapper. Failures don't trace past `FindSets`.

**Dominant failure mode (12/30 total failures):** Models correctly identify that compiler detection starts in `FindSets` but don't trace through to `SetPath` where the PATH is assembled. They expand search paths in `devCFG.pas` without realizing the existing PATH is being corrupted before it's searched. This reflects a reasoning gap — failure to follow the chain: `FindSets` → compiler bin dir → `SetPath` → `GetEnvironmentVariable` → buffer bug.

## Anti-Cheating Analysis

- **Hardcoded outputs**: The FPC behavioral test compiles and runs a program that simulates reading a long PATH (containing `C:\MinGW\bin` + 2100 filler chars) with the extracted buffer size expression. It verifies "MinGW" is preserved in the result — no string literals to hardcode.
- **Overfitting to visible tests**: `pass_to_pass` tests verify procedure structure, string operations, else-branch PATH reading, and other GetEnvironmentVariable calls that the agent cannot predict from `fail_to_pass` tests alone.
- **Modifying test files**: Tests are mounted read-only at `/tests/` by the harness. The agent's patch is applied to `/app/` (the Dev-Cpp repo), not the test directory.
- **Bypassing the intended solution path**: The FPC simulation test extracts the buffer declaration and size expression, compiles them in `{$mode delphiunicode}` (Char=WideChar), and simulates a GetEnvironmentVariable call. Simply removing or stubbing the function would fail the `test_setpath_procedure_exists` and `test_setpath_else_branch_reads_path` checks.
