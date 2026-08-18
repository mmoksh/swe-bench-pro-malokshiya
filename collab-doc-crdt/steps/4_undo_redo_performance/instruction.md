# Milestone 4 — Undo/Redo and Performance

You now have a resilient multi-client document with WAL, snapshots, and sync/merge.

In this milestone, add **per-client undo/redo** respecting causality, improve **performance for large documents**, and implement **tombstone garbage collection**.

## 1. Undo/Redo Model

Each client must have its own undo stack.

### Undo semantics

```text
collab-doc undo <document> --client <client-id>
```

Undo the last operation performed by `<client-id>` that is still applicable.

Rules:

* Only operations authored by that client can be undone by that client (clients cannot undo others' ops)
* Undo must respect causality: if operation B depends on operation A (B inserted after A), undoing A while B still exists should either:
  * also undo B (cascade), OR
  * disallow undo of A until B is undone, returning non-zero with explanation, OR
  * keep B but rehome it to A's predecessor (complicated — only if you want)
  
  Simplest correct approach: disallow undo if dependent operations exist (return non-zero). Or implement stack-based undo where you can only undo the most recent op of that client that has no dependents still present.
* Undoing an insert means deleting that element (logically marking as deleted, keeping tombstone)
* Undoing a delete means resurrecting that element
* Undo itself is an operation that is logged, so redo can replay it
* After undo, format should reflect undone state, status should show correct element count

### Redo semantics

```text
collab-doc redo <document> --client <client-id>
```

Redo the last undone operation for that client.

* If client has undone operations, redo re-applies the most recent undone op
* If no undone operations exist, return non-zero
* Redo must also respect causality (similar checks as undo)
* Redo after new operations have been performed by that client should either clear redo stack (common behavior) or still allow redo if no conflicts — document your choice

### Operation history tracking

To implement per-client undo/redo, maintain:

```json
{
  "undo_stacks": { "alice": [op_id1, op_id2...], "bob": [...] },
  "redo_stacks": { "alice": [...], ... },
  "operation_map": { "op_id": { ... full op ... } }
}
```

Or equivalent. Each client's stack contains operation IDs in order performed.

### Save/load must preserve undo/redo stacks

If a snapshot is saved after some undos, loading that snapshot should preserve ability to redo (or at minimum document whether redo history is preserved; tests will check basic case).

## 2. Extended CLI

### `undo`

```text
collab-doc undo <document> --client <client-id>
```

Example:

```text
collab-doc insert notes --id a --value "Hello" --client alice
collab-doc insert notes --id b --value "world" --client alice --after a
collab-doc undo notes --client alice   # removes b
collab-doc format notes  # should show only "Hello"
collab-doc redo notes --client alice   # brings back b
collab-doc format notes  # should show "Hello\nworld\n"
```

Return non-zero if client has nothing to undo.

### `redo`

```text
collab-doc redo <document> --client <client-id>
```

As described. Return non-zero if nothing to redo.

### `gc` or `compact` (optional but recommended for performance)

```text
collab-doc gc <document>
```

Or:

```text
collab-doc compact <document>
```

Trigger tombstone garbage collection: physically remove deleted elements that are safe to collect (no longer needed for causality).

If you name it differently, also support at least one of those names, or document clearly. Tests will attempt `gc`; if not found they will skip GC assertions but you still must implement internal GC logic triggered automatically or via status.

Implement at least one:

* `collab-doc gc <doc>` 
* or automatic GC when tombstone count exceeds threshold

GC must be safe:
* Only collect tombstones that are not needed for ordering (e.g., no live element's `after` points to a tombstone that would be collected, or you rehome ordering)
* Must not change visible document content (format before GC == format after GC for live elements)
* Must reduce file size or operation log size

Simpler safe GC: collect tombstones where no other operation references them as `after` and they have been deleted longer than some condition, or where all clients have synced past their deletion (vector clock condition). At minimum, you may compact the WAL or remove old operations not needed.

Document your GC safety condition.

## 3. Performance Requirements

The system must handle:

* **Large documents**: at least 10,000 elements (step 1 required 100k ideal, here enforce 10k+ for performance)
* **Many operations**: 10k+ insert/delete operations in sequence must complete in reasonable time (<30s for full sequence via CLI? but we test via Rust unit tests and batch CLI)
* **Efficient lookup**: get by ID should be O(1) average (HashMap)
* **Efficient format**: format of 10k element doc should be <1s
* **Efficient insert**: inserting at arbitrary position should be at most O(n) but not O(n^2) per op amortized leading to O(n^3) total for n inserts (which would timeout)
* **Persistent storage efficiency**: loading a 10k element doc should be <2s

Avoid pathological implementations:
* Do not reload and re-parse entire file multiple times per operation (once per op is okay)
* Do not use O(n^2) algorithm for ordering on each insert (maintain order Vec + HashMap)
* Use buffered IO where appropriate

### Performance Tests

Include benchmarks or performance tests that:

* Insert 5000 elements sequentially and measure time
* Format document with 5000 elements
* Perform 1000 random insert/delete operations
* Load document with 5000 elements from disk

These may be Rust `#[test]` with timing asserts or a separate bench.

## 4. Tombstone Management

Deleted elements become tombstones. Naively keeping all tombstones forever causes unbounded growth.

Implement:

* Tombstone flag on elements (already in step 1)
* GC that can physically remove old tombstones when safe
* Or at least compaction that keeps tombstones but removes old WAL entries not needed

Safety condition examples:

* An element deleted by all clients that have synced (vector clock indicates all clients have seen delete) can be GC'd if no live element's `after` points to it (or if you maintain an alternative ordering structure that doesn't need tombstones for positioning)
* Or GC only when `order` Vec no longer needs to reference tombstone for positioning because you can rehome

Simple GC that is always safe (but partial): if a deleted element is never referenced as `after` by any other element (live or deleted), you may remove it from order and elements map. This handles leaf deletes.

Document what your GC collects and what it leaves.

## 5. Testing Requirements

Extend tests with:

* undo removes last element inserted by client
* undo of delete restores element
* redo reapplies undone operation
* undo returns non-zero when client has no ops to undo
* redo returns non-zero when nothing to redo
* per-client isolation: alice undo does not affect bob's elements, only alice's own ops
* causality: if alice inserts A, bob inserts B after A, alice cannot undo A while B exists unless you implement cascade or rehome — test that either it fails gracefully (non-zero) or it cascades correctly; document and test the chosen behavior
* redo stack cleared after new operation (if you choose that semantics) or preserved — test your documented behavior
* save/load preserves undo stacks or at least doesn't corrupt
* GC (if command exists): after deleting many elements and running GC, format still correct, status elements correct, file size reduced or at least not grown unbounded, and subsequent inserts/deletes still work
* Performance: insert 5000 elements via repeated CLI or via internal API, ensure completes in <10s; format 5000 elements <1s; load 5000 <2s (use Rust tests for perf, not only CLI which has process overhead)
* Large doc with interleaved undo/redo still consistent
* Concurrent clients: alice and bob each insert 100 elements concurrently, merge, verify deterministic format, then undo some and verify

## 6. Completion Criteria

* undo and redo commands implemented for per-client stacks
* undo respects causality (either disallow with non-zero, or cascade correctly, but not corrupt)
* redo works after undo
* per-client isolation: clients only undo own ops
* Tombstone GC implemented (automatic or via gc command) and safe (format preserved)
* Performance: handles 10k elements, format/load within time limits
* All previous milestones still pass
* cargo build, cargo test pass
