# Milestone 5 — Adversarial Hardening and Production Readiness

You now have a feature-complete collaborative document system with multi-client sync, offline recovery, undo/redo, and performance handling.

In this final milestone, harden the system against **adversarial conditions**, **malicious or buggy clients**, **data corruption**, and **high-concurrency stress**.

## 1. Corruption Detection and Handling

### Document integrity verification

Implement:

```text
collab-doc verify <document>
```

Or extend `status` to include corruption check.

`verify` should:

* Check that the document JSON file is valid JSON and matches expected schema
* Check that all element IDs in `order` exist in `elements` map (or are tombstones accounted for)
* Check that no duplicate element IDs exist in order
* Check that operation log is consistent with document state (replay operations and compare — optional but recommended)
* Check that vector clocks are monotonically increasing and consistent with operation counts
* Check that undo/redo stacks reference only existing operation IDs

Exit code 0 if document is healthy, non-zero if corruption detected, with error message to stderr describing issue.

Example:

```text
collab-doc verify notes   # should print "OK" or similar and exit 0 on healthy doc
```

If corruption is detected, the command must not delete or further corrupt data. It may attempt recovery from WAL if possible, but must not make things worse.

### WAL integrity

* WAL entries should be validated on replay: each entry must be valid JSON with required fields
* Corrupted WAL lines (invalid JSON) should be skipped with warning, not cause panic or full doc loss
* Partial WAL writes (truncated last line) should be detected and ignored

### Save file integrity

* `load` must validate snapshot file is valid before overwriting existing document (read and validate first, then write)
* If snapshot is corrupted (invalid JSON), load must return non-zero and not overwrite existing doc

## 2. Byzantine / Malicious Client Handling

Simulate adversarial clients that may send invalid operations. The system must remain correct for honest clients.

The CLI does not have network, so Byzantine handling is about robustness to malformed input and operation validation.

Your implementation must defensively handle:

* **Duplicate element IDs**: already covered, but emphasize deterministic resolution even when malicious client repeatedly tries same ID with different values — document must stay consistent across merges.
* **Invalid after references**: client inserts after non-existent ID — must return non-zero, not corrupt.
* **Deleting already-deleted element**: return non-zero or treat as no-op, but not corrupt.
* **Malformed document file**: if `.collab-doc/<doc>.json` is manually edited to contain invalid data (e.g., duplicate IDs in order, element without ID, order referencing missing ID), `status` / `format` / `verify` should detect and report rather than panic.
* **Operation ID collisions**: operation IDs should be UUIDs; if two ops have same op_id (simulated by directly editing files), second should be treated as duplicate and ignored (idempotent).
* **Clock skew / rollback**: client claims Lamport clock far in future or goes backwards. Your system should accept it but ensure monotonicity per client is eventually enforced? At minimum, should not crash on large Lamport values (u64). If client sends lamport smaller than its last seen, you may either reject or accept and update clock to max — document choice. Key is no panic, no corruption.
* **Very large values**: element value of 1MB or 10MB — should not OOM, should handle gracefully or return error for excessive size with non-zero. At minimum, 100KB values should work.
* **Many clients**: 100+ distinct client IDs should not cause performance collapse.

## 3. Concurrent Edit Storm

The system must handle high-concurrency scenarios:

* 10 clients each inserting 100 elements concurrently at random positions (simulated by interleaving CLI invocations or via Rust multithreaded tests)
* After all inserts + merges, document converges deterministically
* No data loss of honest clients' operations (except legitimate conflict resolution where duplicate ID forces one winner, but that winner rule must be deterministic)
* Format after storm completes in <2s for 1000 elements
* Status after storm shows correct element counts

Stress test via Rust unit tests (not just CLI, to avoid process spawn overhead):

```rust
#[test]
fn test_concurrent_insert_storm() {
    // 5 clients, 200 ops each, random positions, final merge deterministic
}
```

Similar for delete storm:

* Start with 1000 elements, 5 clients randomly deleting 50% each concurrently, merge, verify final state consistent, no panics.

## 4. Determinism Under Adversity

Even under adversarial interleaving, the system must remain deterministic:

* Given same set of operations (same IDs, values, after pointers, client_ids, lamports), final formatted output must be identical regardless of the order operations were applied (as long as causal order is eventually respected via merge)
* Test: take a fixed set of 50 operations from 3 clients, apply in 10 random orders, after each full application + merge, format output must be identical across all 10 runs. Each run starts from clean state.

## 5. Resource Limits and DoS Prevention

Implement basic DoS protection:

* Limit document name length / validation: reject names with path traversal (`../`), with `/`, with null bytes, empty names — return non-zero, don't create file outside .collab-doc dir
* Element ID validation: reject IDs with newlines? Or handle them safely (if you allow any string, ensure formatting/quoting handles it). Safer to restrict to alphanumeric + _- but document whatever you allow. At minimum, prevent empty ID.
* Value size: if value exceeds some threshold (e.g., 1MB), you may reject with clear error, or handle; but must not panic or OOM on 10MB value attempted
* Operation log growth: GC should prevent unbounded growth; status should still be fast even with 10k operations in log
* File descriptor handling: ensure files are closed even on error paths

## 6. Extended CLI Robustness

All commands must:

* Return non-zero on invalid arguments (missing required args, unknown flags) — clap does this by default
* Not panic on unexpected input — use Result and exit 1 with stderr message
* Validate document IDs: prevent directory traversal (`../etc/passwd` should not create file outside .collab-doc). Sanitization: reject any doc name containing `/` or `..` or `.` as path components, or ensure you join safely and canonicalize check.
* Handle special characters in values: values may contain newlines, quotes, unicode, etc. Ensure CLI quoting works and persistence preserves them exactly (round-trip). Tests will include values with `\n`, `"`, `'`, emoji, etc.

### `verify` command (required for this milestone)

```text
collab-doc verify <document>
```

As described in section 1. Prints health status and exits 0 if healthy, non-zero if corruption detected.

If you choose not to add new `verify` binary subcommand and instead want to extend `status` to do verification, you must still support `verify` as alias or documented command — tests will try `verify` first, fallback to `status --verify` or similar, but having explicit `verify` is required.

## 7. Security Considerations

Although this is a local CLI, document in code comments or README:

* How you prevent path traversal in doc names
* How you handle large inputs
* How operation IDs are generated securely (UUID v4)
* That document files are stored with restrictive permissions? Not required but good practice.

## 8. Testing Requirements for Hardening

This milestone's tests are the most demanding — they are **adversarial**.

Include:

* **Corruption detection**: manually corrupt doc file (duplicate ID in order, order references missing ID, invalid JSON), run verify/status, ensure it returns non-zero or detects corruption without panic
* **WAL corruption**: write invalid JSON line to WAL, run status/format, ensure it doesn't panic, recovers or ignores bad line
* **Path traversal**: `collab-doc new ../../tmp/evil` should fail with non-zero and not create file outside .collab-doc
* **Large value**: insert element with 100KB value, verify get returns same value, format includes it (or at least doesn't panic)
* **Many clients**: create document, insert from 50 distinct clients, status reports clients correctly, merge all 50
* **Concurrent storm**: 5 clients × 100 inserts concurrent (interleaved), final state deterministic across multiple runs with same operations but different application order — test convergence
* **Determinism**: fixed set of 50 ops applied in 10 random orders, final format identical
* **Idempotency under storm**: applying same operation twice during storm doesn't duplicate or corrupt
* **Undo/redo under concurrency**: while concurrent inserts happening, undo/redo still works for respective client
* **Save/load of corrupted doc**: save after corruption should either fail or save what it can, load of corrupted snapshot should fail without overwriting healthy doc
* **GC safety under concurrency**: run GC while concurrent ops happening (simulated via Rust threads) — should not corrupt, format before/after GC for live elements same

Also run existing tests from milestones 1-4 — they must still pass. Hardening should not break functionality.

Performance under adversity:

* After adversarial tests, document with 5000 elements + 2000 tombstones should still format in <2s
* Verify of large document (5000 elements) should be <2s

## 9. Final Production Readiness

Before finishing:

* Run:

```text
cargo build --release
cargo test
```

Both must pass.

* Run CLI manually through all commands:

```text
collab-doc new testdoc
collab-doc insert testdoc --id a --value "Hello" --client alice
collab-doc insert testdoc --id b --value "world" --client bob --after a
collab-doc sync testdoc --from alice --to bob
collab-doc merge testdoc --clients alice,bob
collab-doc format testdoc
collab-doc status testdoc
collab-doc save testdoc --path /tmp/snap.json
collab-doc load --path /tmp/snap.json --doc-id testdoc2
collab-doc format testdoc2
collab-doc undo testdoc --client alice
collab-doc redo testdoc --client alice
collab-doc verify testdoc
collab-doc gc testdoc
```

All should succeed (exit 0) except undo/redo edge cases where no ops left — those return non-zero correctly.

* Check that binary is at `target/release/collab-doc` or `target/debug/collab-doc` and can be invoked via `cargo run -- <args>`.

* If you use `assert_cmd` or similar dev dependencies, ensure they don't break release build.

## 10. Completion Criteria

* verify command implemented and detects corruption
* Path traversal prevented
* Corruption handling: invalid JSON/docs don't panic, return non-zero with clear message
* WAL corruption handling: invalid lines skipped, not fatal
* Large values handled (100KB works)
* Many clients (50+) handled
* Concurrent edit storm (5×100) converges deterministically
* Determinism test: same ops, different apply order, same final format
* Resource limits: doc name validation, not OOM on large value
* All previous milestone tests still pass
* Performance still acceptable after hardening
* cargo build, cargo test pass, no panics on adversarial inputs
