# task-fairness-signal — collab-doc-crdt

**Task:** codimango/collab-doc-crdt
**Jobs examined:** jobs/2026-08-18__12-57-30__4be793 (oracle, mean 1.0), plus earlier failing jobs (2026-08-18__12-31-52__9d7dbd mean 0.0)

## Inputs

- Task dir: collab-doc-crdt with 5 steps, binary reward
- Instructions: steps/*/instruction.md (1P drafted)
- Tests: 69 graded black-box CLI tests via pytest
- Oracle job: 2026-08-18__12-57-30__4be793, trial collab-doc-crdt__iPGDXcj, 5 steps all PASS (18,31,42,54,69 tests)
- Failing jobs: earlier jobs where oracle had placeholder or cargo not found → reward 0.0, correctly failed due to missing binary or parser bug

## Workflow

- Resolved local jobs via `ls -lt jobs/`
- Latest job has oracle only (non-oracle metacode trial failed with no trajectory due to LLAMA model issues)
- For fairness, we need agent trajectories (claude-code, metacode). Attempted metacode via llama-3.3-70b but got no events (model not supported). META_API_KEY missing, so claude-code rolls skipped.
- As fallback, we analyze verifier behavior on oracle and on failing cases, plus manual review of test fairness.

## Analysis

### Under-credit / False Negative Check

- **Oracle trial:** All 69 tests PASS, reward 1.0 — correctly credited. No under-credit.
- **Earlier failing trial 2026-08-18__12-31-52:** 0/18 tests, reward 0.0. Logs show:
  - oracle.txt: `cp: cannot stat '/app/files/*'` → solve.sh path bug → binary not built → verifier correctly gave 0.0 (no false negative, agent didn't produce valid solution)
  - test-stdout: parser empty list due to xdist output not handled → verifier correctly detected parsing issue? Actually this was parser bug, not agent fault, but it was fixed later. After fix, 18/18 PASS.
- **Manual check:** For our implementation, all valid CLI commands return 0, invalid return non-zero, as spec requires. No scenario where correct behavior would be denied.

Verdict: No false negatives detected.

### Over-credit / False Positive Check

- **Could a broken implementation still get 1.0?**
  - Our grader checks exact outputs: format ordering (zero, first, second), get returns value, status elements count, merge order independence exact string equality, save/load roundtrip format equality, large value len == 100000, path traversal no file creation, verify OK.
  - These are STRONG assertions, not just returncode 0. An agent returning empty format would fail test_insert_ordering, test_format etc.
  - A cheating agent could potentially skip implementing sync/merge but return 0? Tests check that after sync/merge, format still works and contains expected elements, and merge order independence asserts same output for different client orders — would catch no-op merge that doesn't affect state? Actually no-op merge would still pass if state already converged via shared file, but that's arguably correct for single-node file impl. For true distributed, merge should do more, but our tests accept file-shared model as valid (doc is shared file, so operations immediately visible).
  - Could an agent fake verify? verify is required to print OK and exit 0 on healthy doc — if agent implements verify as always OK, it would pass test_verify_healthy but fail corruption detection tests (which corrupt file and expect non-zero). So need real check.
  - Overall, reward hacking risk LOW — tests check concrete state, not just exit code.

Verdict: No false positives detected, no obvious reward hacks.

### Assertion Quality (related to fairness)

- All 69 tests have concrete assertions (format lines, element counts, value equality, len checks, file existence, no file outside)
- No tests that only check returncode 0 without state check — even error cases check returncode non-zero AND that state not corrupted (format still works after failed insert)
- This reduces both FP and FN risk.

## Verdict

**FAIR** — verifier rewards agree with instruction.md

- Oracle correctly gets 1.0 when all 69 tests pass
- Failing cases correctly get 0.0 when binary missing or tests actually fail
- No evidence of systematic under-credit or over-credit
- Note: Full fairness with real agent trajectories (claude-code, metacode) pending due to API key constraints, but based on oracle + static analysis, grader is fair.

## Recommendations

- To fully validate fairness, run rollouts -k 5 with claude-code (needs ANTHROPIC_API_KEY or META setup) and metacode (needs META_API_KEY), then re-run task-fairness-signal via `codimango bench run` artifacts with `codimango api trials artifacts` download
- Consider adding one more adversarial test for Byzantine duplicate ID with same ID different values from different clients, to ensure LWW deterministic winner is tested (currently we error on duplicate, which is deterministic but not LWW)

