# Milestone 5 — Adversarial Validation and Production Hardening

Harden the existing Rust `collab-doc` application so that it remains correct, durable, deterministic, and performant under adversarial workloads.

The application already supports document editing, persistence, multi-client synchronization, offline operation, crash recovery, undo, redo, and large-document workloads. Treat the current implementation as potentially containing subtle bugs.

Your task is to systematically find and fix those bugs.

The repository is the primary deliverable. Do not merely report failures. Reproduce them, determine their root causes, implement fixes, add regression tests, and rerun the relevant validation.

## 1. Establish a Clean Baseline

Start by creating a clean build and running the complete existing test suite.

Run:

```text
cargo build --release
cargo test
```

Exercise the CLI through fresh subprocesses rather than relying only on in-process tests.

Record the initial test results and identify any existing failures before making changes.

Do not assume that passing existing tests means the implementation is correct.

## 2. Adversarial Multi-Client Workloads

Construct workloads involving multiple independent clients.

Clients should independently perform combinations of:

* insertions;
* deletions;
* modifications;
* undo;
* redo;
* synchronization;
* offline editing;
* reconnection;
* process restart.

Do not synchronize clients after every operation.

Allow clients to develop substantially different operation histories before exchanging state.

For example:

```text
Client A: 100 local operations
Client B: 150 local operations
Client C: 75 local operations

Then exchange operations in arbitrary orders.
```

After communication has completed, verify that all clients converge to the same logical document state.

Repeat the workload with different operation and delivery orders.

## 3. Adversarial Message Delivery

Test synchronization under hostile delivery conditions.

Generate message schedules containing arbitrary combinations of:

* reordering;
* duplication;
* delay;
* repeated delivery;
* partial delivery;
* long gaps between messages.

A message may arrive many times and in an order completely unrelated to the order in which it was generated.

For a fixed logical workload, generate many different delivery schedules.

The final document must be independent of the delivery schedule.

If a failure occurs, preserve the exact operation set and delivery schedule that produced it.

Reduce the failure to the smallest reproducible case and add it to the regression suite.

## 4. Randomized State-Machine Testing

Build a randomized state-machine test that models clients and their interactions.

Generate operations such as:

```text
insert
delete
modify
undo
redo
sync
disconnect
reconnect
restart
```

Allow random actions to occur on different clients.

Maintain an independent reference model where practical and compare the implementation against it.

Run sufficiently long sequences to expose interactions that are unlikely to appear in ordinary unit tests.

Do not stop after finding one failure. Fix failures and continue testing until repeated randomized runs remain stable.

Use deterministic random seeds so that failures can be reproduced.

## 5. Crash and Recovery Stress Testing

Combine crash injection with synchronization and editing.

Terminate clients at arbitrary points during:

* local operations;
* persistence;
* synchronization;
* acknowledgement;
* recovery;
* undo;
* redo.

After each crash:

1. restart the process;
2. recover persistent state;
3. continue operating;
4. synchronize with other clients;
5. verify document consistency.

Also test repeated crashes:

```text
edit
→ crash
→ recover
→ sync
→ edit
→ crash
→ recover
→ sync
→ edit
→ crash
→ recover
```

The application must remain recoverable and must not silently lose durable state.

## 6. Persistence Corruption Testing

Test the behavior of the application when persistent files contain unexpected data.

Construct cases involving:

* truncated files;
* incomplete records;
* invalid identifiers;
* invalid operation types;
* malformed serialized values;
* duplicated records;
* unexpected fields;
* partially written state.

The application must fail safely.

It must not silently convert corrupted persistent state into an incorrect valid-looking document.

Where recovery is possible, verify that recovery produces the correct state.

Where recovery is impossible, return a clear error without destroying unrelated persistent data.

## 7. Idempotence and Repetition

Repeated actions must not unexpectedly change logical state.

Test repeated:

```text
sync
sync
sync
```

as well as repeated delivery of the same operations.

Also test repeated:

```text
recover
recover
recover
```

and repeated process restarts.

After the system reaches a stable state, performing additional synchronization or recovery operations should not change the document.

## 8. Undo/Redo Stress Testing

Exercise undo and redo under complicated histories.

Generate sequences containing:

* many consecutive edits;
* many consecutive undos;
* many consecutive redos;
* edits after undo;
* synchronization between undo and redo;
* concurrent edits from other clients;
* offline edits;
* restarts;
* crashes.

Verify that undo only affects the appropriate logical operation and does not accidentally remove unrelated changes.

Verify that all clients eventually converge after synchronization.

Pay particular attention to long histories where a naive implementation may consume excessive memory or become unexpectedly slow.

## 9. Large-Scale Testing

Generate substantially larger workloads than the normal unit tests.

Test documents with at least:

* 100,000 elements;
* hundreds of thousands of operations;
* long synchronization histories;
* multiple independent clients.

Measure:

* execution time;
* peak memory;
* persistent storage size;
* synchronization volume;
* startup/recovery time.

Look for performance degradation that becomes apparent only at scale.

Use profiling to identify the actual source of significant bottlenecks.

Fix problems that violate the application's practical resource requirements.

## 10. CLI Black-Box Validation

Treat the CLI as the public interface.

Exercise every command through independent subprocesses.

Verify:

* correct exit codes;
* stdout contents;
* stderr contents;
* persistence between invocations;
* behavior after process termination;
* behavior after recovery;
* behavior for invalid arguments;
* behavior for missing documents;
* behavior for missing clients;
* behavior for malformed input.

Test combinations rather than isolated commands.

For example:

```text
new
→ create client
→ insert
→ insert
→ sync
→ offline
→ edit
→ restart
→ online
→ sync
→ undo
→ redo
→ format
→ status
```

The exact CLI contract must remain unchanged.

## 11. Regression Discipline

Every bug discovered during this milestone must result in a regression test whenever practical.

For each failure:

1. reproduce it;
2. isolate the cause;
3. minimize the failing workload;
4. identify the violated invariant;
5. fix the underlying implementation;
6. add a regression test;
7. rerun the regression;
8. rerun the broader test suite.

Do not fix failures by:

* disabling tests;
* reducing test coverage;
* ignoring an operation;
* silently dropping messages;
* hard-coding expected results;
* adding arbitrary timing delays;
* special-casing individual test inputs.

## 12. Final Validation

After making all necessary fixes, perform a clean validation from the final repository state.

Run:

```text
cargo build --release
cargo test
```

Run the complete black-box CLI suite.

Run randomized tests using multiple deterministic seeds.

Run crash-injection tests.

Run persistence corruption tests.

Run large-document benchmarks.

Repeat important tests after a fresh build to ensure the result does not depend on stale artifacts or process-local state.

## Acceptance Criteria

The milestone is complete only when:

1. The project builds successfully from a clean state.
2. The complete Rust test suite passes.
3. All black-box CLI tests pass.
4. Multi-client randomized workloads converge.
5. Arbitrary message ordering does not change the final logical state.
6. Duplicate message delivery does not corrupt state.
7. Offline edits survive process restarts.
8. Crash recovery preserves durable state.
9. Repeated recovery is safe.
10. Malformed persistent state is handled safely.
11. Undo/redo remains correct under concurrent and offline workloads.
12. Large documents and long operation histories can be processed successfully.
13. Significant performance problems have been investigated and addressed.
14. Every important bug discovered during validation has corresponding regression coverage.
15. No tests have been disabled, weakened, or bypassed.
16. No required functionality remains stubbed or silently ignored.

Do not declare completion while known correctness failures remain.

The final repository, executable behavior, automated tests, and measured performance are the primary deliverables.

Provide a concise final report containing:

* the major issues discovered;
* the fixes implemented;
* the regression tests added;
* final test results;
* final performance measurements;
* any remaining limitations.
