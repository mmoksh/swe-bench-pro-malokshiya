# codimango/collab-doc-crdt

## Task: Local-First Collaborative Document System

Build a CRDT-based collaborative rich-text document system in Rust from scratch.
The system supports concurrent editing across multiple clients, offline operation
with crash recovery, and production-grade conflict resolution.

## Domain

Distributed systems / CRDTs / Rust CLI + library

## Milestones

| Step | Name | Focus |
|------|------|-------|
| 1 | Core Document Engine | CRDT data structure (RGA/tree), rich-text ops (insert/delete/format), logical clocks |
| 2 | Multi-Client Sync | Multi-client state, operation serialization, merge/sync, causal ordering |
| 3 | Offline + Crash Recovery | WAL persistence, snapshot + incremental save, offline queueing, reconciliation |
| 4 | Undo/Redo + Performance | Per-client undo/redo respecting causality, large doc handling, tombstone GC |
| 5 | Adversarial Hardening | Concurrent edit storms, Byzantine clients, corruption detection, stress tests |

## CLI Contract

```
collab-doc new <doc-id>
collab-doc insert <doc-id> --client <id> --pos <n> --text "..."
collab-doc delete <doc-id> --client <id> --pos <n> --len <n>
collab-doc format <doc-id> --client <id> --start <n> --end <n> --bold/--italic/--heading <n>
collab-doc get <doc-id> [--client <id>] [--format plain|json|html]
collab-doc sync <doc-id> --from <client> --to <client>
collab-doc merge <doc-id> --clients <a>,<b>
collab-doc save <doc-id> --path <file>
collab-doc load --path <file> --doc-id <id>
collab-doc undo <doc-id> --client <id>
collab-doc redo <doc-id> --client <id>
collab-doc status <doc-id>
```

## Reward

Binary (pass/fail). Each step's `min_reward = 1.0`.

## Type

Greenfield (tbench-multi). Empty /app, agent builds from scratch.

## Author

Mohammed Alokshiya (malokshiya@meta.com)
