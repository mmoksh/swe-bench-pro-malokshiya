
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
