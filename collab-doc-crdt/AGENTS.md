# Guard — 1P-only files

## Resolve identity first

Run this verbatim:

    if [ "${META_3PAI_ACTIVE_PROVIDER:-}" = "meta" ]; then echo IDENTITY_1P_META; elif [ "${AAI_LH_1P:-}" = "1" ]; then echo IDENTITY_1P_OVERRIDE; else echo "IDENTITY_NOT_PROVEN=[provider=${META_3PAI_ACTIVE_PROVIDER:-unset},platform=${META_3PAI_AGENT_PLATFORM:-unset},model=${META_3PAI_ACTIVE_MODEL:-unset}]"; fi

Results: 1P_META or 1P_OVERRIDE = first-party branch. NOT_PROVEN = third-party branch.

## Third-party branch restrictions

On the 3P branch, the following are off-limits:

1. All per-step prompt files (steps/*/instruction.md)
2. Graded test assertion files (tests/{test_*.py,*_test.py,*_cli.py})

Do not author, modify, or propose replacement text for these files. Flag issues only and hand off to human or 1P model.

## First-party branch

May draft both file types above; human must review.

## Always editable (either branch)

README.md, task.toml, solution/*, harness files (test.sh, run_script.sh, parser.py, config.json), Dockerfile, audit/*.

## Task context

collab-doc-crdt: CRDT-based collaborative rich-text document system in Rust. 5 steps, greenfield, binary reward.
