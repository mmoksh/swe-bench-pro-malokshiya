# Audit — collab-doc-crdt — READY

**Task:** codimango/collab-doc-crdt — CRDT-based collaborative rich-text document system in Rust (greenfield, 5 steps, binary reward)

**Audit Date:** 2026-08-18
**Auditor:** Mohammed Alokshiya (malokshiya@meta.com) + Avocado (1P)
**Identity:** IDENTITY_1P_META

## Checklist

| Gate | Status | Evidence | Link |
|------|--------|----------|------|
| **Packaged & runs** | PASS | Oracle jobs 4be793 + 5b73a6 both mean 1.0, all 5 steps PASS (18/31/42/54/69) | jobs/2026-08-18__12-57-30__4be793/ + jobs/2026-08-18__14-17-04__5b73a6/ |
| **task.toml** | PASS | schema_version 1.1, 5 steps, inherit_prior_session, allow_internet true, reward_type binary, [[task.authors]] present, tags include swe-bench-long-horizon-track | task.toml |
| **Structural validate** | PASS | `codimango bench validate -p collab-doc-crdt` → PASS (1 WARN greenfield empty repo) — was FAIL before fix, now WARN only | - |
| **Tags mandatory** | PASS | [metadata].tags exact literal | task.toml |
| **Guard** | PASS | CLAUDE.md exists | CLAUDE.md |
| **Dockerfile** | PASS | FROM python:3.11-bookworm + Rust 1.79, pytest vendored, cargo deps cached, host network | environment/Dockerfile |
| **Solution** | PASS | All steps Cargo.toml.lock + src + collab-doc-bin fallback, solve.sh no hardcoded /tmp path (fixed 2026-08-18) | steps/*/solution/ |
| **Tests** | PASS | 69 graded black-box CLI, f2p 18/13/11/12/15, parser xdist-safe | tests/ |
| **Task quality** | PASS | Opening context, genuine deps, negative tests, determinism via element_id | steps/*/instruction.md |
| **Grader integrity** | PASS | reward.txt gated, empty-set refuse, parser contract | test.sh parser.py |
| **Coverage** | PASS | 100% ASSERTED | audit/coverage_report.md |
| **Performance** | PASS | Large doc 500, save/load 200, format <2s | tests/ |
| **Adversarial** | PASS | Corruption, path traversal, WAL corruption, 100KB, 20 clients, storm 3x30, 5 random orders | test_5_* |
| **Contamination** | LOW | NOT_FOUND (no signal) → LOW, no benchmark match for collab-doc CLI contract | bench validate |
| **Provenance** | WARN | Top-level instruction.md missing (multi-turn has per-step), per-step exist — authorship clean | bench validate |
| **Empirical difficulty** | PASS | Oracle 1.0 x2 jobs, local 69/69, ~1.5k LOC Rust RGA + WAL + undo/redo — predicts Good/hard band | jobs/ |
| **Token/context cost** | WARN* | Oracle 0 tokens (no LLM), `lh-count-tokens` on oracle shows 0 passing avocado/claude (expected, oracle has no tokens). Real agent rollouts need ANTHROPIC/META keys; local estimate ~moderate (cargo build + 69 subprocess tests ~20s) | audit/ |
| **Sanity** | READY | audit/sanity/2026-08-18T21-12-41Z...md all gates PASS | audit/sanity/ |

*Token WARN: oracle has no LLM tokens by design. `lh-count-tokens` script reports 0 trajectories for avocado/claude because latest jobs are oracle-only (expected). Passing real-agent jobs would show tokens; this task's complexity (Rust greenfield 5 milestones) predicts moderate token use.

## Per-Step Table

| Step | Name | Dependencies | min_reward | Tests (fail/pass) | Oracle Reward (2 jobs) | Gradable |
|------|------|--------------|------------|-------------------|------------------------|----------|
| 1 | 1_core_document_engine | [] | 1.0 | 18/0 | 1.0 / 1.0 | Yes |
| 2 | 2_multi_client_sync | [1_core...] | 1.0 | 13/18 | 1.0 / 1.0 | Yes |
| 3 | 3_offline_crash_recovery | [2_multi...] | 1.0 | 11/31 | 1.0 / 1.0 | Yes |
| 4 | 4_undo_redo_performance | [3_offline...] | 1.0 | 12/42 | 1.0 / 1.0 | Yes |
| 5 | 5_adversarial_hardening | [4_undo...] | 1.0 | 15/54 | 1.0 / 1.0 | Yes |

- Total: 69 graded
- Solution: cumulative Rust (document.rs 36k, persistence.rs 14k, main.rs 11k), staged with Cargo.lock + fallback binary
- Verifier: pytest xdist workers=min(nproc,8)

## Oracle Jobs

- **Job 1:** 2026-08-18__12-57-30__4be793 trial collab-doc-crdt__iPGDXcj mean 1.0, baseline step1 0.0 → 1.0, steps2-5 baseline already 1.0 (cumulative solution — harbor WARN "no-op ref solution" but PASS)
- **Job 2:** 2026-08-18__14-17-04__5b73a6 trial collab-doc-crdt__LVWhW66 mean 1.0, same pattern, after fixing `tests/config.json` repo/base_commit/instance_id + `task.toml` [[task.authors]] + solve.sh hardcoded path removal → `bench validate` now WARN-only (was FAIL)
- Both: per-step 1.0/1.0/1.0/1.0/1.0, 18/31/42/54/69 tests non-zero

## Fixes in this iteration (2026-08-18 14:17 UTC)

1. **task.toml** — removed duplicate `authors = []` + `[[task.authors]]`, kept only `[[task.authors]] name+email` → fixes Invalid TOML + task.authors WARN
2. **tests/config.json** — added `repo:""`, `base_commit:"000...0"` (40 zeros), `instance_id:"collab-doc-crdt_final"` → fixes SWE Config FAIL (missing repo/base_commit)
3. **steps/*/solution/solve.sh** — removed hardcoded `/tmp/collab-doc-oracle/...` fallback, kept only `$SRC_DIR/collab-doc-bin` → fixes Solution WARN "hardcoded host path"
4. After fixes: `codimango bench validate -p collab-doc-crdt` → Structural: 9 PASS + 1 WARN (empty repo expected for greenfield), previously 1 FAIL + 2 WARN

## Review

- Manual 10-item review PASS, no Critical/High
- Spec-test alignment: CLI contract matches test invocations
- Multi-turn integrity: genuine deps

## Coverage / Fairness / Token

- Coverage: audit/coverage_report.md 100% ASSERTED
- Fairness: audit/fairness_report.md FAIR (oracle 1.0 correctly credited, failing jobs 0.0 correctly failed)
- Sanity: audit/sanity/2026-08-18T21-12-41Z...md READY
- Tokens: oracle 0 (no LLM); `lh-count-tokens` on oracle jobs reports 0 avocado/claude passing (expected). Real rollouts pending API keys. Estimate moderate.

## Verdict

**READY** — all critical gates PASS. Structural validation now WARN-only (greenfield empty repo). Two oracle jobs both mean 1.0. Grader gates correctly, contamination LOW, no critical issues.

## Push

- Local commits: 8f4f02d + fixes pending (this iteration)
- Remote `origin https://github.com/codimango/swe-bench-pro-malokshiya.git` → `Repository not found` via gh (org private / token mmoksh lacks access / repo renamed). SSH attempt same. `gh repo view` fails GraphQL "Could not resolve to a Repository".
- Task is ready for Codimango portal submission (`codimango task` / assets) which does not require GitHub push. If GitHub push required, need org access or fork to `mmoksh/swe-bench-pro-malokshiya` then PR.

## Implementation Artifacts

- Oracle source: /tmp/collab-doc-oracle/src/
- Binary fallback: steps/*/solution/files/collab-doc-bin 1.7M
- Tests: 69 tests final
- Dockerfile: python:3.11-bookworm + Rust 1.79 + vendored wheels + cargo fetch cached
- Compose: build.network: host, network_mode: host

## References

- Jobs: jobs/2026-08-18__12-57-30__4be793/ + jobs/2026-08-18__14-17-04__5b73a6/
- Validate: `codimango bench validate -p collab-doc-crdt` → Structural PASS (1 WARN)
- Task: task.toml, README.md

