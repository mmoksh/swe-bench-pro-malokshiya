# Milestone 3 — Offline Operation and Crash Recovery

You now have a multi-client document system with causal ordering and sync/merge from milestone 2.

In this milestone, make the system **resilient to crashes and network partitions** by implementing Write-Ahead Logging (WAL), snapshotting, offline operation queuing, and reconciliation.

## 1. WAL Persistence

Implement a Write-Ahead Log for each document:

* Before applying any operation to the main document file, append the operation to a WAL file.
* WAL file location: `.collab-doc/<doc>.wal` or similar alongside the main document file. Choose a deterministic path your implementation documents.
* Each WAL entry must contain full operation data: op_id, client_id, lamport, kind, timestamp.
* On startup (any CLI command), check if WAL exists and has entries not yet reflected in main file — replay WAL to recover.
* WAL must be fsynced or at least flushed to survive process crashes (use file sync where appropriate, or at least ensure buffered writes are flushed).

### Crash Recovery Semantics

After a crash (simulated by killing process mid-write or by existing WAL containing ops not yet checkpointed):

* `collab-doc status <doc>` must recover and show correct counts
* `collab-doc format <doc>` must show recovered state
* No operations already acknowledged to client may be lost

## 2. Extended CLI: save / load Snapshot

### `save`

```text
collab-doc save <document> --path <file-path>
```

Save a snapshot of the current document state to an arbitrary file path. The snapshot format is implementation-defined (JSON 권장) but must contain:

* all live elements with IDs and values and ordering
* all operations (or at least sufficient to reconstruct)
* vector clocks / lamport clocks per client
* client list

The snapshot file should be self-contained and portable.

Example:

```text
collab-doc save notes --path /tmp/notes.snapshot.json
```

Return non-zero if document not found or path not writable.

### `load`

```text
collab-doc load --path <file-path> --doc-id <document-id>
```

Load a document from a snapshot file created by `save`. Creates or overwrites the document with ID `<document-id>` from the snapshot.

If document ID already exists, overwrite it (or return error but implementation must be consistent — document in tests which you choose; overwriting is simpler).

Example:

```text
collab-doc load --path /tmp/notes.snapshot.json --doc-id notes2
collab-doc format notes2  # should equal original notes format
```

Save/load must preserve:
* element ordering
* element values
* client clocks
* operation history (if applicable)

Round-trip requirement:

```text
save doc --path X
load --path X --doc-id doc2
format doc == format doc2
status doc elements == status doc2 elements
```

## 3. Offline Operation Queue

Simulate offline operation: clients may perform operations while "offline", queuing them locally, then syncing later.

Implementation approach (choose one and document):

* Option A: per-client offline queue file `.collab-doc/<doc>.<client>.offline` that stores operations not yet merged into main doc. When client goes "offline" (config file or flag), operations go to queue. On `sync`, queue is flushed.
* Option B: main WAL already serves as offline queue — all ops go to WAL and are considered pending until merge.

Simplest that satisfies tests: even if you treat offline as same as online (operations immediately visible), you must support a mechanism where operations can be replayed after a crash and `save`/`load` captures the complete state.

However, to demonstrate understanding, implement at minimum:

* If `.collab-doc/<doc>.wal` exists with pending ops, any command loads and applies them before proceeding.
* Ability to tolerate missing or partial writes: if main JSON file is corrupted or truncated (simulated by tests truncating file), recover from WAL if possible, or at least return non-zero with clear error rather than panic and not delete unrelated documents.

### Reconciliation

After offline period:

* Client B's queued ops should be mergeable into main document via `sync` or `merge`
* After reconciliation, all clients converge to same state
* Causality must still be respected — queued ops must have proper Lamport clocks assigned at queue time, not at sync time

## 4. Atomic Writes and Fsafety

Main document file should be written atomically:

* Write to temp file `.collab-doc/<doc>.json.tmp` then rename to `.collab-doc/<doc>.json` (atomic on POSIX)
* This prevents corruption if crash occurs mid-write
* WAL write should happen before main file write (WAL = redo log)

Implement at least one of:
* atomic rename for main file
* or check file integrity on load (validate JSON, check required fields), recover from WAL on invalid

## 5. Persistence Guarantees to Test

* After each successful insert/delete, killing and restarting (new CLI invocation) preserves that operation
* Simulate crash during write: after truncating main file, WAL replay should recover (or at least status should detect corruption and not panic)
* Save creates portable file, load recreates identical logical document
* Save/load round-trip preserves format output exactly
* Large document save/load works (1000+ elements)
* Offline queue: operations performed while "offline" (if you implement explicit offline mode) are not lost

## 6. New Files and Storage Layout

Document your storage layout in a comment or README inside src:

```
.collab-doc/
  <doc>.json         — main document state (atomic writes)
  <doc>.wal          — write-ahead log (append-only, JSON lines or array)
  <doc>.<client>.offline — optional per-client offline queue
```

Or equivalent. The tests use black-box CLI, so they don't assert file layout, but they will check that files exist and that recovery works.

## 7. Testing Requirements

Extend test suite with:

* save creates file and returns 0
* load recreates document with same format output
* save/load round-trip preserves element count and ordering
* save/load preserves client clocks (if status includes client info, verify after round-trip)
* crash recovery: perform ops, forcefully keep WAL with extra op not yet checkpointed (simulated by directly writing to WAL file in test), then run status/format and verify recovery
* atomic write simulation: concurrent CLI invocations don't corrupt document (run two inserts in parallel from different processes, final doc should have both or at least not be corrupted JSON)
* offline queue: if implemented, queue ops while offline and verify they appear after sync
* load overwrites existing doc or merges appropriately — define and test
* save of large doc (500+ elements) and load succeeds
* error cases: save non-existent doc returns non-zero, load non-existent file returns non-zero
* format after save/load equals format before

## 8. Completion Criteria

* WAL file written for each operation and replayed on startup
* save and load commands implemented with correct exit codes
* save/load round-trip preserves logical document content
* Atomic writes prevent corruption on crash (rename pattern)
* Recovery from WAL on startup works (or at least corruption detected gracefully)
* Offline ops not lost (WAL serves as offline queue at minimum)
* All previous milestones still pass
* cargo build, cargo test pass
