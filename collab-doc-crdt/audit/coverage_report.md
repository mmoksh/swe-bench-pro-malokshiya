# Grader Strength - Coverage Report

## Summary
- Total graded tests: 69
- Per-step coverage: 100% of CLI commands tested, negative cases, persistence, determinism, performance, adversarial

## Step 1: Core Document Engine (18 tests)
Requirements from instruction.md:
- [ASSERTED] Create document (new) - test_new_document
- [ASSERTED] Insert single - test_insert_single
- [ASSERTED] Insert ordering (beginning) - test_insert_ordering
- [ASSERTED] Insert after - test_insert_after
- [ASSERTED] Delete - test_delete
- [ASSERTED] Delete unknown fails - test_delete_unknown
- [ASSERTED] Duplicate ID fails - test_duplicate_element_id
- [ASSERTED] Insert after unknown fails - test_insert_after_unknown
- [ASSERTED] Get not found fails - test_get_not_found
- [ASSERTED] Format empty - test_format_empty
- [ASSERTED] Status - test_status
- [ASSERTED] Persistence across invocations - test_persistence_across_invocations
- [ASSERTED] Empty value - test_empty_value
- [ASSERTED] Special characters - test_special_characters
- [ASSERTED] Many operations (100) - test_many_operations
- [ASSERTED] Combined workflow - test_combined_workflow
- [ASSERTED] Large document (500) - test_large_document
- [ASSERTED] Idempotent recovery - test_idempotent_recovery

Coverage: 18/18 requirements ASSERTED ✓

## Step 2: Multi-Client Sync (13 tests, plus 18 from step1 as pass_to_pass)
- [ASSERTED] Insert with --client - test_insert_with_client
- [ASSERTED] Multi-client format visible - test_multi_client_format
- [ASSERTED] Sync command - test_sync_command
- [ASSERTED] Merge command - test_merge_command
- [ASSERTED] Merge order independence - test_merge_order_independence
- [ASSERTED] Status includes clients - test_status_clients
- [ASSERTED] Log command - test_log_command
- [ASSERTED] Log filter client - test_log_filter_client
- [ASSERTED] Concurrent inserts deterministic - test_concurrent_inserts_deterministic
- [ASSERTED] Causal ordering (sync then insert after) - test_causal_ordering
- [ASSERTED] Merge three clients - test_merge_three_clients
- [ASSERTED] Client clock preserved - test_client_clock_preserved_after_reload
- [ASSERTED] Backward compat no client - test_backward_compat_no_client

Coverage: 13/13 new requirements ASSERTED, plus regression from step1 PASS ✓

## Step 3: Offline + Crash Recovery (11 new, 31 prior)
- [ASSERTED] Save creates file - test_save_creates_file
- [ASSERTED] Load recreates - test_load_recreates
- [ASSERTED] Save/load roundtrip - test_save_load_roundtrip
- [ASSERTED] Save/load preserves status - test_save_load_preserves_status
- [ASSERTED] Save nonexistent fails - test_save_nonexistent_fails
- [ASSERTED] Load nonexistent fails - test_load_nonexistent_fails
- [ASSERTED] WAL exists - test_wal_exists_after_ops
- [ASSERTED] WAL recovery on truncation - test_wal_recovery_on_truncation
- [ASSERTED] Large save/load (200) - test_large_save_load
- [ASSERTED] Save/load preserves clients - test_save_load_preserves_clients
- [ASSERTED] Atomic write no corruption - test_atomic_write_no_corruption_parallel

Coverage: 11/11 ASSERTED ✓

## Step 4: Undo/Redo + Performance (12 new, 42 prior)
- [ASSERTED] Undo insert - test_undo_insert
- [ASSERTED] Undo delete restores - test_undo_delete_restores
- [ASSERTED] Redo after undo - test_redo_after_undo
- [ASSERTED] Undo no ops fails - test_undo_no_ops_fails
- [ASSERTED] Redo no ops fails - test_redo_no_ops_fails
- [ASSERTED] Per-client isolation - test_per_client_isolation
- [ASSERTED] Undo causality - test_undo_causality
- [ASSERTED] GC preserves format - test_gc_preserves_format
- [ASSERTED] GC removes tombstones - test_gc_removes_tombstones
- [ASSERTED] Large doc performance (1000) - test_large_doc_performance
- [ASSERTED] Save/load preserves undo - test_save_load_preserves_undo
- [ASSERTED] Undo/redo multiple - test_undo_redo_multiple

Coverage: 12/12 ASSERTED ✓

## Step 5: Adversarial Hardening (15 new, 54 prior)
- [ASSERTED] Verify healthy - test_verify_healthy
- [ASSERTED] Verify detects duplicate order - test_verify_detects_duplicate_order
- [ASSERTED] Verify detects missing ref (graceful) - test_verify_detects_missing_ref
- [ASSERTED] Path traversal blocked - test_path_traversal_blocked
- [ASSERTED] WAL corruption handled - test_wal_corruption_handled
- [ASSERTED] Large value (100KB) - test_large_value
- [ASSERTED] Many clients (20) - test_many_clients
- [ASSERTED] Concurrent storm deterministic (3x30) - test_concurrent_storm_deterministic
- [ASSERTED] Determinism random apply order - test_determinism_random_apply_order
- [ASSERTED] Special chars preserved - test_special_chars_preserved
- [ASSERTED] Save/load corrupted snapshot fails - test_save_load_corrupted_snapshot
- [ASSERTED] GC safety under load - test_gc_safety_under_load
- [ASSERTED] Verify after GC - test_verify_after_gc
- [ASSERTED] Idempotent ops during storm - test_idempotent_ops_during_storm
- [ASSERTED] Undo/redo under concurrency - test_undo_redo_under_concurrency

Coverage: 15/15 ASSERTED ✓

## Overall
- All 5 steps have 100% spec-completeness: every CLI command and behavior described in instruction.md has at least one ASSERTED test
- No UNTESTED requirements
- No COVERED-BUT-UNASSERTED (all covered via CLI assertions)
- Performance tests included for large docs
- Adversarial tests cover corruption, path traversal, large values, many clients, concurrent storms, determinism

## Grader Integrity
- test.sh writes reward file (reward.txt 1/0) gated on fail_to_pass/pass_to_pass
- fail_to_pass non-empty for each step ✓
- parser handles both xdist and non-xdist output ✓
- No empty fail_to_pass trap ✓
- Binary reward with min_reward 1.0 ✓

Verdict: Grader strength GOOD

