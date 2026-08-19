
import subprocess
import json
import os
import tempfile
import shutil
import uuid
import pytest

BIN = "/app/target/release/collab-doc"
if not os.path.exists(BIN):
    BIN = "/tmp/collab-doc-oracle/target/release/collab-doc"
    if not os.path.exists(BIN):
        BIN = "collab-doc"

def run(args, cwd=None, check=True):
    result = subprocess.run([BIN] + args, cwd=cwd, capture_output=True, text=True)
    return result

def run_ok(args, cwd=None):
    r = run(args, cwd=cwd)
    assert r.returncode == 0, f"Expected 0 but got {r.returncode}: {' '.join(args)}\nstdout={r.stdout}\nstderr={r.stderr}"
    return r

def run_fail(args, cwd=None):
    r = run(args, cwd=cwd)
    assert r.returncode != 0, f"Expected non-zero but got 0: {' '.join(args)}"
    return r

@pytest.fixture
def workdir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)

def test_new_document(workdir):
    run_ok(["new", "notes"], cwd=workdir)
    run_fail(["new", "notes"], cwd=workdir)

def test_insert_single(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello"], cwd=workdir)
    r = run_ok(["get", "doc", "--id", "a"], cwd=workdir)
    assert "Hello" in r.stdout

def test_insert_ordering(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "first"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "second", "--after", "a"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "c", "--value", "zero"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    lines = r.stdout.strip().split("\n")
    assert lines == ["zero", "first", "second"]

def test_insert_after(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--after", "a"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "A" in r.stdout and "B" in r.stdout

def test_delete(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "world", "--after", "a"], cwd=workdir)
    run_ok(["delete", "doc", "--id", "a"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert r.stdout.strip() == "world"
    run_fail(["get", "doc", "--id", "a"], cwd=workdir)

def test_delete_unknown(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_fail(["delete", "doc", "--id", "nonexistent"], cwd=workdir)

def test_duplicate_element_id(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "v1"], cwd=workdir)
    run_fail(["insert", "doc", "--id", "a", "--value", "v2"], cwd=workdir)

def test_insert_after_unknown(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_fail(["insert", "doc", "--id", "a", "--value", "v", "--after", "nonexistent"], cwd=workdir)

def test_get_not_found(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_fail(["get", "doc", "--id", "x"], cwd=workdir)

def test_format_empty(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert r.stdout.strip() == ""

def test_status(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello"], cwd=workdir)
    r = run_ok(["status", "doc"], cwd=workdir)
    assert "elements: 1" in r.stdout
    assert "operations: 1" in r.stdout

def test_persistence_across_invocations(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "Hello" in r.stdout

def test_empty_value(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", ""], cwd=workdir)
    r = run_ok(["get", "doc", "--id", "a"], cwd=workdir)
    assert r.returncode == 0

def test_special_characters(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    val = "Hello world quotes"
    run_ok(["insert", "doc", "--id", "a", "--value", val], cwd=workdir)
    r = run_ok(["get", "doc", "--id", "a"], cwd=workdir)
    assert "Hello" in r.stdout

def test_many_operations(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    for i in range(100):
        after = f"elem_{i-1}" if i > 0 else None
        args = ["insert", "doc", "--id", f"elem_{i}", "--value", f"value_{i}"]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    r = run_ok(["status", "doc"], cwd=workdir)
    assert "elements: 100" in r.stdout

def test_combined_workflow(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "world", "--after", "a"], cwd=workdir)
    run_ok(["delete", "doc", "--id", "a"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "c", "--value", "hi"], cwd=workdir)
    r = run_ok(["get", "doc", "--id", "c"], cwd=workdir)
    assert "hi" in r.stdout
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "hi" in r.stdout and "world" in r.stdout
    r = run_ok(["status", "doc"], cwd=workdir)
    assert "elements: 2" in r.stdout

def test_large_document(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    n = 500
    for i in range(n):
        after = f"e{i-1}" if i>0 else None
        args = ["insert", "doc", "--id", f"e{i}", "--value", f"v{i}"]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    r = run_ok(["status", "doc"], cwd=workdir)
    assert f"elements: {n}" in r.stdout

def test_idempotent_recovery(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "Hello" in r.stdout
    # second format should give same result
    r2 = run_ok(["format", "doc"], cwd=workdir)
    assert r.stdout == r2.stdout

# --- Realistic rich-text & trace additions (keep tiny tests above for edge cases) ---

RICH_TEXT_SAMPLES = [
    "# Project Proposal\n## Overview\nCollaborative editing with CRDTs",
    "## Agenda\n- Introductions\n- **Goals** and *Objectives*",
    "**Bold Title** Introduction paragraph with *italic emphasis* and **bold** mixed, plus `code` snippet.",
    "### Design Decisions\n> Blockquote: *We chose RGA for* **deterministic merge**.",
    "- [ ] Task **Write spec** *due tomorrow*\n- [x] Task **Prototype** done",
    "Paragraph with **nested *italic inside bold?*** and normal text spanning multiple sentences. Lorem ipsum dolor sit amet.",
    "# Heading 1\nContent under heading with **bold** and *italic* and `inline code` and [link](http://example.com)",
    "```python\ndef hello():\n    print(\"world\")\n```\nAbove code block with **annotation**",
    "Table: | Col A | Col B |\n|-------|-------|\n| **Bold** | *Italic* |",
    "Final notes: **Summary** *All participants* agreed. Next steps: ## Action Items\n1. **Ship** 2. *Iterate*",
]

def test_rich_text_headings_bold_italic(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    for i, val in enumerate(RICH_TEXT_SAMPLES):
        args = ["insert", "doc", "--id", f"rt{i}", "--value", val]
        if i > 0:
            args += ["--after", f"rt{i-1}"]
        run_ok(args, cwd=workdir)
    # verify each element retrievable and format preserves order
    for i, val in enumerate(RICH_TEXT_SAMPLES):
        r = run_ok(["get", "doc", "--id", f"rt{i}"], cwd=workdir)
        assert val[:20] in r.stdout, f"rich text rt{i} not preserved"
    r = run_ok(["format", "doc"], cwd=workdir)
    # every sample's distinctive marker should appear
    for needle in ["# Project Proposal", "**Bold Title**", "## Agenda", "```python", "Table:"]:
        assert needle in r.stdout
    r = run_ok(["status", "doc"], cwd=workdir)
    assert f"elements: {len(RICH_TEXT_SAMPLES)}" in r.stdout

def test_realistic_document_trace_50_ops(workdir):
    """Realistic single-author trace: 50+ ops building a rich document linearly."""
    run_ok(["new", "doc"], cwd=workdir)
    trace = [
        ("p0", "# Sprint Planning Q3\n## Goals", None),
        ("p1", "### Attendees: Alice, Bob, Carol, Dave", "p0"),
        ("p2", "- **Alice**: *Facilitator* - leads discussion", "p1"),
        ("p3", "- **Bob**: *Engineering* - owns CRDT core", "p2"),
        ("p4", "## Timeline\n| Week | Milestone | Owner |", "p3"),
        ("p5", "| W1 | **Core engine** | Bob |", "p4"),
        ("p6", "| W2 | *Multi-client sync* | Alice |", "p5"),
        ("p7", "| W3 | **Offline recovery** | Carol |", "p6"),
        ("p8", "### Risks\n> *Network partitions* may delay **sync**.", "p7"),
        ("p9", "```rust\nfn merge(a: Op, b: Op) -> Op { /* ... */ }\n```", "p8"),
    ]
    # extend with 45 more realistic paragraphs
    for i in range(10, 55):
        if i % 5 == 0:
            val = f"## Section {i}\nContent for section {i} with **bold {i}** and *italic {i}*"
        elif i % 5 == 1:
            val = f"- Item {i}: **Task {i}** assigned to *owner{i%4}* priority **P{i%3}**"
        elif i % 5 == 2:
            val = f"Paragraph {i}: Lorem ipsum **dolor** sit *amet* consectetur adipiscing elit {i}."
        elif i % 5 == 3:
            val = f"> Quote {i}: *Insight {i}* — **Author {i}**"
        else:
            val = f"`code_{i}` snippet with **result {i}** and *note {i}*"
        after = f"p{i-1}"
        trace.append((f"p{i}", val, after))
    for eid, val, after in trace:
        args = ["insert", "doc", "--id", eid, "--value", val]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "# Sprint Planning Q3" in r.stdout
    assert "fn merge" in r.stdout
    # spot-check middle and tail
    assert "Section 50" in r.stdout or "Section 40" in r.stdout
    r = run_ok(["status", "doc"], cwd=workdir)
    assert "elements: 55" in r.stdout
    # delete + re-insert realistic edit
    run_ok(["delete", "doc", "--id", "p2"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "Facilitator" not in r.stdout
    run_ok(["insert", "doc", "--id", "p2_v2", "--value", "- **Alice**: *Facilitator* (updated) **confirmed**", "--after", "p1"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "confirmed" in r.stdout

def test_large_stress_1500_elements(workdir):
    """Larger stress: 1500 sequential inserts with realistic mixed content."""
    run_ok(["new", "doc"], cwd=workdir)
    n = 1500
    for i in range(n):
        after = f"s{i-1}" if i > 0 else None
        # realistic-ish value: mix of heading/bold/italic every 100
        if i % 100 == 0:
            val = f"# Chapter {i//100} **Intro {i}** *notes*"
        elif i % 10 == 0:
            val = f"**Bold block {i}** with *italic {i}* and text"
        else:
            val = f"line {i} value_{i} lorem"
        args = ["insert", "doc", "--id", f"s{i}", "--value", val]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    r = run_ok(["status", "doc"], cwd=workdir)
    assert f"elements: {n}" in r.stdout
    r = run_ok(["format", "doc"], cwd=workdir)
    assert f"line {n-1}" in r.stdout

def test_unicode_and_special_rich_text(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    samples = [
        ("u0", "## Unicode: café naïve résumé — **bold café** *italic naïve*"),
        ("u1", "Emoji mix: 🚀 **Launch** *success* 🎉 with heading # Go"),
        ("u2", "Math: ∑ ∫ √ ∞ **theorem** *proof* `x^2`"),
        ("u3", "RTL-ish: مرحبا **bold** *italic* mixed"),
    ]
    for eid, val in samples:
        after = samples[samples.index((eid,val))-1][0] if samples.index((eid,val))>0 else None
        args = ["insert", "doc", "--id", eid, "--value", val]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    for eid, val in samples:
        r = run_ok(["get", "doc", "--id", eid], cwd=workdir)
        assert val[:10] in r.stdout
