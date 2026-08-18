# Milestone 2 — Multi-Client Sync and Causal Ordering

You now have a working core document engine from milestone 1 that supports persistent ordered documents with stable element IDs using operations like insert and delete.

In this milestone, extend the system to support **multiple collaborating clients** editing the same document concurrently, with proper **causal ordering** and **conflict resolution**.

## 1. Extend the Document Model for Collaboration

The document must now track which client performed each operation.

Each operation must record:
* `client_id` — which client performed it (string identifier)
* `lamport` — a Lamport timestamp (u64, monotonically increasing per client, max of seen + 1 on merge)
* `op_id` — unique operation identifier remains

Maintain per-client **vector clocks** or at minimum Lamport clocks to establish causal relationships.

The system must be deterministic: given the same set of operations regardless of arrival order, the final document state must be identical after all operations are applied in causal order.

## 2. Extended CLI Contract

Preserve all commands from milestone 1. The existing commands continue to work without --client (defaulting to a "default" client). Additionally:

### `insert` with --client

```text
collab-doc insert <document> --id <id> --value <value> [--after <element-id>] [--client <client-id>]
```

If --client is provided, record that client as the operation's author and assign a Lamport timestamp. The operation's Lamport clock must be one greater than that client's previous clock value, or derived from the max clock seen.

Example:
```text
collab-doc insert notes --id a --value "Hello" --client alice
collab-doc insert notes --id b --value "world" --client bob --after a
```

### `delete` with --client

```text
collab-doc delete <document> --id <id> [--client <client-id>]
```

Record the client performing the deletion.

### `sync` — Sync operations from one client to another view

```text
collab-doc sync <document> --from <source-client> --to <target-client>
```

This command simulates syncing operations: ensure that operations authored by source-client are visible when querying as target-client. In a single-node file-based implementation, this means operations are globally visible (the document is shared), but the command must succeed and record that a sync occurred between those clients. It should return non-zero if the document doesn't exist.

For richer implementations, it may also merge vector clocks.

Example:
```text
collab-doc sync notes --from alice --to bob
```

### `merge` — Merge multiple clients' operations

```text
collab-doc merge <document> --clients <client-a>,<client-b>[,<client-c>...]
```

Merge and reconcile operations from the listed clients into a consistent document state. The result must be deterministic regardless of the order clients are listed.

After merge, formatting the document should yield the same result irrespective of merge order.

The merge must:
* preserve all non-conflicting operations
* resolve concurrent inserts at the same position deterministically (e.g., by client_id lexicographic tie-breaker after Lamport comparison)
* maintain element ID uniqueness (if two clients insert same ID concurrently, one must win deterministically, or return error but remain consistent)
* be idempotent — merging twice yields same state

Example:
```text
collab-doc merge notes --clients alice,bob
collab-doc format notes
```

### `log` or `ops` — List operations (optional but recommended)

```text
collab-doc log <document> [--client <client-id>]
```

Print the operation log. If --client is given, filter to that client's ops. Output format is implementation-defined but should include op_id, client_id, lamport, and kind. This helps debugging and is used by tests to verify causal ordering.

### `status` extended

`status` must now also report:

```text
clients: <number or list>
```

or at minimum include per-client information. Keep backward compatible with milestone 1 format that already includes:

```
elements: <n>
operations: <n>
```

Add clients info in addition, not instead. Example:

```
elements: 5
operations: 8
clients: alice,bob
```

Or:

```
elements: 5
operations: 8
clients: 2
```

Either is acceptable as long as the word "clients" appears and parsing can extract client count or list.

## 3. Causal Ordering Requirements

Implement **causal consistency**:

* If operation B causally depends on operation A (B's client had seen A before performing B), then any client must observe A before B after sync/merge.
* Concurrent operations (no causal relationship) may be ordered deterministically (e.g., Lamport timestamp, then client_id).
* The Lamport clock rule: on each operation by client C, lamport = max(current_clock_C, max_lamport_seen_from_other_clients) + 1, and store per-client max.
* Operations list returned by `log` should be in causal order (or at least its sorted order should respect causality).

### Vector Clock (optional but encouraged)

Maintain a vector clock per client to track causality. The document's persisted state should include:

```json
{
  "vector_clocks": { "alice": 3, "bob": 2 },
  ...
}
```

Even if you use Lamport clocks for ordering, tracking per-client sequence numbers helps detect concurrent edits.

## 4. Conflict Resolution

Define deterministic rules for:

* **Concurrent inserts after same element**: if Alice and Bob both insert after X concurrently, the final order between their inserts must be deterministic. Use (lamport, client_id) tie-breaker: smaller lamport wins; if equal, lexicographically smaller client_id wins. The "winner" appears first after X. Or you may order by element_id as final tie-breaker — but document and keep deterministic.
* **Concurrent deletes**: if two clients delete same element concurrently, second delete should be treated as no-op or error but not corrupt state.
* **Insert after deleted element**: if element Y was deleted, inserting after Y should still work by finding the nearest alive predecessor, or fail gracefully with non-zero exit and clear message — but remain consistent.
* **Duplicate element IDs across clients**: if two clients concurrently insert different values with same element ID, exactly one must win deterministically (e.g., higher lamport wins, or client_id tie-breaker). No duplicate IDs in final document. This is critical for convergence.

## 5. Persistence Extended

Persist:
* vector clocks / lamport clocks per client
* client list
* all operations with client_id and lamport
* sync history (optional)

Documents must still persist across CLI invocations, now with client information preserved.

## 6. Testing Requirements

Extend tests from milestone 1 to cover:

* inserting with --client
* operations from multiple clients visible in format
* sync command succeeds
* merge command converges to same state regardless of client order
* causal ordering: client B inserting after seeing client A's op should place after A even if concurrent
* concurrent inserts at same position have deterministic order
* duplicate element ID resolution is deterministic and convergent
* status reports clients
* log shows operations with client and lamport
* loading a document preserves client clocks
* random interleavings of operations from 2-3 clients produce deterministic final state after merge
* idempotency: same op applied twice doesn't corrupt; merging twice yields same state

Create black-box tests that invoke CLI from multiple simulated clients.

Example scenario:

```text
new doc
insert doc --id a --value "A" --client alice
insert doc --id b --value "B" --client bob --after a
insert doc --id c --value "C" --client alice --after a
sync doc --from alice --to bob
merge doc --clients alice,bob
format doc  # should be deterministic
```

## 7. Completion Criteria

* All milestone 1 functionality still works (backward compat)
* --client flag accepted on insert/delete
* sync and merge commands implemented and return 0 on valid inputs
* Causal ordering respected: causally dependent ops ordered correctly
* Concurrent inserts resolved deterministically
* Duplicate IDs resolved deterministically, no duplicates in final state
* Status includes clients info
* Persistence includes client clocks
* Tests cover multi-client scenarios including concurrent edit storms of 2-3 clients
* cargo build and cargo test still pass
