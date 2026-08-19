# Milestone 3 — Offline Editing and Crash Recovery

Extend the existing Rust `collab-doc` application so that clients can continue editing while disconnected and reliably recover from process crashes.

The existing document and synchronization functionality must continue to work.

The primary deliverable is the working repository. Implement the functionality, create tests, run experiments, investigate failures, and iterate until the acceptance criteria are satisfied.

## 1. Offline Editing

A client must be able to make document changes without communicating with another client.

When a client is offline:

* local edits must continue to work;
* edits must be persisted locally;
* generated operations must not be lost;
* the client must retain enough information to synchronize its changes later.

An offline client may perform an arbitrary sequence of insertions, deletions, and modifications.

After reconnecting, its operations must be incorporated into the shared document correctly.

For example:

```text
alice goes offline
alice performs 100 edits
alice process exits
alice process restarts
alice reconnects
```

All durable edits must still be available for synchronization.

## 2. Durable Synchronization State

Persist the information necessary for a client to determine:

* which operations it has generated;
* which operations it has received;
* which operations have been incorporated into its local state;
* which operations still need to be synchronized.

This state must survive process termination.

Restarting a client must not cause it to forget previously received operations or unnecessarily regenerate operations that it has already persisted.

Repeated synchronization after a restart must remain safe and idempotent.

## 3. Client Restart

A client may terminate at any point during normal operation.

After restarting, it must recover its local document and synchronization state from persistent storage.

Test scenarios including:

```text
create client
→ make edits
→ terminate process
→ restart
→ inspect document
```

and:

```text
create client
→ make edits
→ terminate process
→ restart
→ synchronize
→ verify convergence
```

The recovered state must be equivalent to the state that existed before termination, subject to operations that had not yet been durably persisted.

Define the persistence boundary clearly in the implementation.

## 4. Server Persistence

The synchronization system must maintain persistent shared state.

Restarting the server or synchronization store must not lose operations that had already been durably recorded.

After restart, clients must be able to reconnect and continue synchronization.

Test:

```text
client A creates operations
→ synchronization store persists them
→ synchronization service terminates
→ synchronization service restarts
→ client B reconnects
→ client B receives the operations
```

The final document must be correct.

## 5. Crash Injection

Add a mechanism for deliberately terminating a process at important points during an operation.

At minimum, test crashes around:

* before an operation is persisted;
* after an operation is persisted;
* before synchronization state is updated;
* after synchronization state is updated;
* before an acknowledgement is recorded;
* after an acknowledgement is recorded.

You may implement crash injection through an environment variable, test-only configuration, or another mechanism appropriate for the repository.

The crash mechanism must allow automated tests to reproduce failures deterministically.

Do not treat a process crash as an exceptional condition that can simply be ignored.

## 6. Persistence Ordering

Carefully reason about the ordering between:

1. applying an operation;
2. persisting the operation;
3. updating synchronization metadata;
4. acknowledging the operation.

A crash between any two of these stages must not leave the persistent state in a form that silently loses or corrupts an operation.

In particular, distinguish between:

* an operation that was never persisted;
* an operation that was persisted but not acknowledged;
* an operation that was acknowledged;
* an operation that was received but not yet applied.

Use tests and fault injection to validate the behavior rather than relying solely on reasoning.

## 7. Recovery

When a process restarts after a crash, it must inspect its persistent state and recover to a valid state.

Recovery must be:

* deterministic;
* repeatable;
* safe to execute more than once.

If the application finds partially written or otherwise invalid persistent state, it must handle it safely.

It must not silently construct a corrupted document from incomplete data.

Where recovery can determine that an operation needs to be replayed, replaying it must not corrupt the document.

## 8. Synchronization After Failure

Clients must be able to synchronize correctly after crashes.

Test combinations such as:

```text
A edits
→ A crashes
→ A restarts
→ B edits concurrently
→ A synchronizes with B
```

and:

```text
A edits offline
→ A crashes
→ A restarts
→ B synchronizes
→ B edits
→ A synchronizes again
```

Also test repeated failures:

```text
edit
→ crash
→ recover
→ sync
→ edit
→ crash
→ recover
→ sync
```

The system must continue to converge.

## 9. Repeated Synchronization

Synchronization may be interrupted at any point.

A client may:

* send the same operations repeatedly;
* reconnect multiple times;
* receive duplicate operations;
* crash during synchronization;
* restart and retry the same synchronization.

The system must remain correct under all of these conditions.

Running synchronization twice must not change the final document after the first successful synchronization.

## 10. CLI Contract

Extend the existing CLI with:

### `offline`

Mark a client as disconnected from synchronization.

```text
collab-doc offline <document> --client <client-id>
```

### `online`

Reconnect a client.

```text
collab-doc online <document> --client <client-id>
```

### `recover`

Explicitly recover a client's persistent state.

```text
collab-doc recover <document> --client <client-id>
```

Recovery should normally happen automatically when necessary, but this command must provide a way to invoke and test recovery explicitly.

### `sync`

The existing synchronization command must continue to work after offline periods and process restarts:

```text
collab-doc sync <document> --from <client-id> --to <client-id>
```

Do not change the existing command names or previously defined flags.

## 11. Persistence Testing

Create tests that repeatedly:

1. create a document;
2. perform operations;
3. terminate the process;
4. start a fresh process;
5. inspect the state;
6. continue editing;
7. synchronize;
8. verify convergence.

Use separate subprocesses for important black-box tests so that the implementation cannot accidentally rely on process-local memory.

Include tests involving large numbers of operations.

## 12. Randomized Failure Testing

Create randomized tests that combine:

* local edits;
* offline periods;
* synchronization;
* duplicate operations;
* message reordering;
* client restarts;
* synchronization-store restarts;
* crashes at persistence boundaries.

For each workload, eventually reconnect the clients and allow synchronization to complete.

Verify that:

* no durable operation is silently lost;
* documents remain internally consistent;
* clients eventually converge;
* repeated recovery does not change the logical state.

When a randomized test fails, reduce it to a reproducible sequence, identify the violated invariant, fix the underlying problem, and add a regression test.

## Acceptance Criteria

The milestone is complete only when:

1. Clients can edit documents while offline.
2. Offline edits survive client restarts.
3. Synchronization works after arbitrary offline periods.
4. Persistent synchronization state survives process termination.
5. Durably recorded operations survive synchronization-store restarts.
6. Recovery correctly handles crashes at persistence boundaries.
7. Replaying recovered operations does not corrupt state.
8. Repeated synchronization remains idempotent.
9. Existing synchronization and document behavior continues to work.
10. Required CLI commands and flags are implemented.
11. Black-box subprocess tests pass.
12. Randomized failure tests pass.
13. Crash-injection tests pass.
14. No durable operation is silently lost.
15. No test is disabled or weakened to hide a failure.

Before finishing, run:

```text
cargo build --release
cargo test
```

and run the complete black-box CLI test suite using fresh processes.

Provide a concise final report describing the implementation, recovery strategy, tests performed, and any remaining issues.
