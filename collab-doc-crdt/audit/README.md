# Audit — collab-doc-crdt — READY (2026-08-19)

**Task:** codimango/collab-doc-crdt — CRDT-based collaborative rich-text document system in Rust (greenfield, 5 steps, binary reward)
**Audit Date:** 2026-08-19T20:10Z
**Auditor:** Mohammed Alokshiya (malokshiya@meta.com) + Avocado (1P)
**Identity:** IDENTITY_1P_META (provider=meta, model=avocado-code-latest, platform=metacode)
**Repo-Type:** New repo / greenfield (tbench-multi) — empty /app, agent builds Rust project from scratch
**Parallel Verifier:** Yes — pytest-xdist vendored, run_script.sh min(nproc,8) cap, serial fallback, parser handles both orderings

## Checklist

| Gate | Status | Evidence | Link |
|------|--------|----------|------|
| **Packaged & runs** | PASS | Structural validate WARN-only (empty repo inherent greenfield) 9 PASS +1 WARN, sanity READY, oracle mean 1.0 x2 jobs, local 101/101 PASS (67s) + cargo build 8.26s | audit/sanity/2026-08-19T20-09-46Z__devvm37936.nha0.facebook.com__malokshiya.md + jobs/2026-08-18__12-57-30__4be793/ + jobs/2026-08-18__14-17-04__5b73a6/ |
| **task.toml** | PASS | schema_version 1.1, 5 steps 1_core_document_engine→5_adversarial_hardening, deps chain, inherit_prior_session true 2-5, allow_internet true, reward_type binary, author_name/email present, tags include multi-turn + swe-bench-long-horizon-track (mandatory), category_usecase new_library, subdomain distributed_systems, format swe_bench_multi_turn, workstream swe_public_repo | task.toml |
| **Structural validate** | PASS | codimango bench validate → 9 PASS +1 WARN (SWE Config empty repo) — greenfield expected | - |
| **Tags mandatory** | PASS | [metadata].tags contains exact literal swe-bench-long-horizon-track | task.toml |
| **Guard** | PASS | CLAUDE.md + AGENTS.md exist with HARD RULE + identity resolver, 1P branch | CLAUDE.md |
| **Dockerfile** | PASS | FROM python:3.11-bookworm + Rust 1.79, vendored wheels pytest 8.4.2 xdist 3.8.0, cargo deps cached, host network, /app + /logs, offline verify | environment/Dockerfile |
| **Solution** | PASS | All steps Cargo.toml.lock + src (document.rs 36k, persistence.rs 14k, main.rs 11k) + collab-doc-bin 1.6M fallback, solve.sh APP_DIR=/app, no hardcoded /tmp, exit 0 | steps/*/solution/ |
| **Tests** | PASS | 69 graded required (18/13/11/12/15) + 32 extended =101 total, parser xdist-safe (pattern1+pattern2), run_script parallel cap 8 + serial fallback, test.sh reward gated bool(all_required) and (all_required <= passed) | tests/config.json + tests/test_6_strict_requirements.py |
| **Task quality** | PASS | Opening context clear (step1 frames greenfield Rust CLI), genuine deps (core→sync→offline→undo→hardening), no re-spec, no hints, CLI contract exact, determinism via element_id, no leaks | steps/*/instruction.md |
| **Grader integrity** | PASS | reward.txt + reward.json, defensive casing fail_to_pass fallback, empty-set refuse, node-id consistency, no angle brackets, binary min_reward 1.0 all steps | audit/sanity/ |
| **Coverage** | PASS | 100% ASSERTED — all 69 requirements mapped, no UNTESTED, spec-completeness 18/13/11/12/15, plus extended realism 50/72/1000 ops | audit/coverage_report.md |
| **Performance** | PASS | Large doc 500/1500/2000, save/load 200/1000, rich-text, format <2s, concurrent storm 3x30 deterministic, many clients 20+50, WAL replay + atomic write | tests/test_4_undo_redo_performance.py + test_5_adversarial_hardening.py |
| **Adversarial** | PASS | Path traversal blocked, WAL corruption handled, corrupted snapshot rejected, duplicate order detection via verify, special chars + unicode, Byzantine WAL, GC safety under load, undo/redo under concurrency, vector clock monotonic/causal/multi-client | tests/test_5_adversarial_hardening.py + test_6_strict_requirements.py |
| **Contamination** | MEDIUM (NOT_FOUND→MEDIUM in new validator) | Previous audit LOW NOT_FOUND no benchmark match, new bench validate returned NOT_FOUND server-side but mapped to MEDIUM due to 429 retries; no positive signal, no clone of existing repo, CLI contract novel | bench validate |
| **Provenance** | PASS (WARN top-level instruction.md missing expected multi-turn) | Per-step instruction.md exist 350/355/324/306/371 lines, authored 1P, graded tests authored 1P (previous iteration), harness/config any model, no unauthorized text | bench validate |
| **Empirical difficulty** | PASS (Good/hard band estimated) | Oracle 1.0 x2 jobs + local 101/101, ~1.5k LOC Rust RGA + WAL + undo/redo + vector clocks, 5 milestones, 69 graded black-box subprocess (~20-67s), no fresh claude-code/metacode rollouts due to missing META_API_KEY but complexity hard, predicts Good band | jobs/ + local pytest |
| **Token/context cost** | WARN* | Oracle 0 tokens (oracle has no LLM); lh-count-tokens on oracle jobs reports 0 avocado/claude passing (expected). Real agent rollouts need ANTHROPIC/META keys; local estimate ~moderate (cargo build 8s + 69+32 tests 67s) ~20k tokens final-turn estimate | audit/ |
| **Sanity** | READY | audit/sanity/2026-08-19T20-09-46Z...md all gates PASS (23 checks) | audit/sanity/ |

*Token WARN oracle by design.

## Per-Step Table

| Step | Name | Dependencies | min_reward | Tests (f2p/p2p) | Oracle Reward (jobs 4be793/5b73a6) | Local 101 | Gradable | Solution LOC |
|------|------|--------------|------------|-----------------|-----------------------------------|-----------|----------|--------------|
| 1 | 1_core_document_engine | [] | 1.0 | 18/0 +4 ext | 1.0 / 1.0 | 22 PASS | Yes | document.rs 978l baseline |
| 2 | 2_multi_client_sync | [1_core...] | 1.0 | 13/18 | 1.0 / 1.0 (cumulative WARN expected) | 17 ext PASS | Yes | +client/clock/merge/log |
| 3 | 3_offline_crash_recovery | [2_multi...] | 1.0 | 11/31 | 1.0 / 1.0 | 14 ext PASS | Yes | +WAL/save/load/atomic |
| 4 | 4_undo_redo_performance | [3_offline...] | 1.0 | 12/42 | 1.0 / 1.0 | 15 ext PASS | Yes | +undo/redo/GC/vector clock |
| 5 | 5_adversarial_hardening | [4_undo...] | 1.0 | 15/54 | 1.0 / 1.0 | 18 +13 ext PASS | Yes | +verify/path-traversal/adversarial |

- Total required: 69 graded (fail_to_pass)
- Total with extended: 101 PASS local 2026-08-19
- Solution: cumulative Rust, staged with Cargo.lock + fallback binary 1.7M, APP_DIR writes to /app
- Verifier: pytest xdist workers=min(nproc,8) cap, -v, serial fallback, parser handles both orderings

## Oracle Jobs (freshness)

- **Job 1:** 2026-08-18__12-57-30__4be793 trial collab-doc-crdt__iPGDXcj mean 1.0, baseline step1 0.0→1.0 correct, steps2-5 baseline 1.0 cumulative (harbor WARN "no-op ref solution" expected for cumulative greenfield) — PASS
- **Job 2:** 2026-08-18__14-17-04__5b73a6 trial collab-doc-crdt__LVWhW66 mean 1.0 after fixing tests/config.json repo/base_commit/instance_id + task.toml [[task.authors]] + solve.sh hardcoded path removal → validate WARN-only
- **Local 2026-08-19:** cargo build --release 8.26s target/release/collab-doc 1.6M, pytest tests/ 101 passed in 67.59s

## Review (manual lh-review-task equivalent)

- Opening Context Clarity (step1): Good — frames greenfield Rust CLI, 6 commands new/insert/delete/get/format/status, persistence, operation semantics
- Multi-turn Integrity: Genuine dependency (core→sync→offline→undo→hardening), no weak dep, accumulator acceptable, no overriding bonus but tags context-following implicit, regression coverage present (step N includes N-1 tests as pass_to_pass via top-level config)
- Instruction Quality: Good across steps — conversational user next message, no "you will be tested", exact CLI contract with flags (--id --value --after --client --from --to --path --doc-id), no hints
- Test Quality: Strong — black-box CLI via subprocess, no in-process import coupling, covers negative (duplicate ID, unknown element, nonexistent doc), persistence across invocations, special chars, large docs, concurrent deterministic, causal ordering, WAL truncation, atomic parallel write, per-client undo isolation, GC preserves format, verification detects duplicate/missing ref, path traversal, WAL corruption, 100KB values, 20 clients, storm 3x30, determinism random order, vector clock monotonic/causal/preserved, Byzantine corruption
- Grader: PASS — binary gated bool(all_required), defensive casing, empty-set refuse, reward file not exit code
- Environment: PASS — no future leak, Dockerfile base only, no workdir/setup.sh needed (greenfield), no /tests leak (scaffold default correct)
- Solution: PASS — correct idiomatic Rust RGA-like ordered list with stable IDs, operation log with client lamport clocks, WAL append, snapshot save/load atomic via temp file + rename, undo/redo stacks per-client persisted, GC tombstone removal preserving ordering, verify integrity checking duplicate order + missing ref + truncated
- Breadth: Not homogeneous — 5 distinct milestones
- No Critical/High findings

## Coverage / Fairness / Tokens (Phase 5.5)

- Coverage: audit/coverage_report.md 100% ASSERTED all 5 steps, every CLI command has test
- Fairness: Not yet run via fairness skill, but structurally fair — oracle 1.0 correctly, no 0/0 vacuous
- Tokens: Oracle 0 (no LLM), fresh rollouts pending META_API_KEY, estimate moderate

## Repo-Type + Verifier Decision (Phase 0.5)

- Q1 Repo-type: **New repo / greenfield (tbench-multi)** — task is greenfield new_library distributed_systems, Dockerfile empty /app, agent builds from scratch, category_usecase new_library, Example B pattern
- Q2 Guard ack: IDENTITY_1P_META understood — prompts 1P/human, tests/rubrics 1P/Codex/human, guard installed CLAUDE.md+AGENTS.md
- Q3 Parallel verifier: **Yes** — recommended for CLI (subprocess-bound 0.24s/call), built with pytest-xdist vendored, run_script.sh NPROC capped 8, -v kept, parser both orderings, local 101 tests ~67s (serial fallback would be ~82s for 122 tests equivalent, now ~14s parallel per step)

## Verdict

**READY TO SUBMIT** — all blocking gates PASS. Advisory WARNs only: SWE Config empty repo (inherent greenfield), contamination MEDIUM due to NOT_FOUND cache miss (no positive signal), token WARN oracle by design. No Critical/High open.

## Push Gate (Phase 7)

- Local git: collab-doc-crdt/ clean (no changes since last READY), overall repo has job deletions but task itself clean
- Remote origin https://github.com/codimango/swe-bench-pro-malokshiya.git → previous audit push failed Repository not found via gh (org private / token mmoksh lacks org access). This iteration same remote.
- Task ready for Codimango portal submission which does not require GitHub push. If GitHub push required, need fork to mmoksh/swe-bench-pro-malokshiya or org access.
- Action: Requires explicit user approval per hard gate. Options: Approve push (attempt origin), Commit only local, Discuss/Hold.

## Implementation Artifacts

- Oracle source: steps/5_adversarial_hardening/solution/files/src/ (document.rs 36k, persistence.rs 14k, main.rs 11k)
- Binary fallback: steps/*/solution/files/collab-doc-bin 1.7M
- Tests: 69 required +32 extended =101 final, 6 files
- Dockerfile: python:3.11-bookworm + Rust 1.79 + vendored wheels + cargo fetch cached, build host network
- CLI: collab-doc new/insert/delete/get/format/status/client/sync/merge/log/save/load/undo/redo/gc/compact/verify

## References

- Jobs: jobs/2026-08-18__12-57-30__4be793/ + jobs/2026-08-18__14-17-04__5b73a6/ + local 2026-08-19 101/101
- Validate: codimango bench validate -p collab-doc-crdt → 9 PASS +1 WARN (SWE Config empty repo)
- Sanity: audit/sanity/2026-08-19T20-09-46Z__devvm37936.nha0.facebook.com__malokshiya.md READY
- Coverage: audit/coverage_report.md 100% ASSERTED
- Task: task.toml, README.md, CLAUDE.md, AGENTS.md
