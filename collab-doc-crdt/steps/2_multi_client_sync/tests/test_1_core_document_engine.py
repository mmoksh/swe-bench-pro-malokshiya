"""Step 1 — Core Document Engine — fresh CLI black-box suite (18 tests).

Covers: new/insert/delete/get/format/status, ordering via --after,
persistence, error paths, special chars, large-doc & combined workflows.
All via subprocess CLI; no internal imports.
"""
import os, subprocess, tempfile, shutil, pathlib, json
import pytest

# Binary resolution: prefer built artifact, fall back to PATH
BIN_CANDIDATES = [
    "/app/target/release/collab-doc",
    "/app/target/debug/collab-doc",
    "collab-doc",
]
def _bin():
    for c in BIN_CANDIDATES:
        if "/" in c and os.path.exists(c):
            return c
        if "/" not in c and shutil.which(c):
            return c
    return BIN_CANDIDATES[0]
BIN = _bin()

def cli(*args, cwd=None):
    return subprocess.run([BIN, *args], cwd=cwd, capture_output=True, text=True)

def ok(*args, cwd=None):
    r = cli(*args, cwd=cwd)
    assert r.returncode == 0, f"expected ok: {args} -> {r.returncode}\nSTDOUT:{r.stdout}\nSTDERR:{r.stderr}"
    return r

def fail(*args, cwd=None):
    r = cli(*args, cwd=cwd)
    assert r.returncode != 0, f"expected fail but got ok: {args}\n{r.stdout}"
    return r

@pytest.fixture
def wd():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)

def test_new_document(wd):
    ok("new", "notes", cwd=wd)
    # second new with same id must fail
    fail("new", "notes", cwd=wd)
    # different name succeeds
    ok("new", "other", cwd=wd)

def test_insert_single(wd):
    ok("new", "doc", cwd=wd)
    ok("insert", "doc", "--id", "hx1", "--value", "Hello", cwd=wd)
    r = ok("get", "doc", "--id", "hx1", cwd=wd)
    assert "Hello" in r.stdout

def test_insert_ordering(wd):
    ok("new", "doc", cwd=wd)
    ok("insert", "doc", "--id", "a", "--value", "first", cwd=wd)
    ok("insert", "doc", "--id", "b", "--value", "second", "--after", "a", cwd=wd)
    # c with no --after goes to head
    ok("insert", "doc", "--id", "c", "--value", "zero", cwd=wd)
    r = ok("format", "doc", cwd=wd)
    lines = [l for l in r.stdout.strip().splitlines() if l]
    assert lines == ["zero", "first", "second"], f"got {lines}"

def test_insert_after(wd):
    ok("new", "doc", cwd=wd)
    ok("insert", "doc", "--id", "p", "--value", "P", cwd=wd)
    ok("insert", "doc", "--id", "q", "--value", "Q", "--after", "p", cwd=wd)
    r = ok("format", "doc", cwd=wd)
    lines = r.stdout.strip().splitlines()
    assert lines.index("P") < lines.index("Q")

def test_delete(wd):
    ok("new", "doc", cwd=wd)
    ok("insert", "doc", "--id", "x", "--value", "keep", cwd=wd)
    ok("insert", "doc", "--id", "y", "--value", "remove", "--after", "x", cwd=wd)
    ok("delete", "doc", "--id", "y", cwd=wd)
    r = ok("format", "doc", cwd=wd)
    assert r.stdout.strip() == "keep"
    fail("get", "doc", "--id", "y", cwd=wd)

def test_delete_unknown(wd):
    ok("new", "doc", cwd=wd)
    fail("delete", "doc", "--id", "ghost", cwd=wd)

def test_duplicate_element_id(wd):
    ok("new", "doc", cwd=wd)
    ok("insert", "doc", "--id", "dup", "--value", "v1", cwd=wd)
    fail("insert", "doc", "--id", "dup", "--value", "v2", cwd=wd)

def test_insert_after_unknown(wd):
    ok("new", "doc", cwd=wd)
    fail("insert", "doc", "--id", "n", "--value", "v", "--after", "nope", cwd=wd)

def test_get_not_found(wd):
    ok("new", "doc", cwd=wd)
    fail("get", "doc", "--id", "missing", cwd=wd)

def test_format_empty(wd):
    ok("new", "doc", cwd=wd)
    r = ok("format", "doc", cwd=wd)
    assert r.stdout.strip() == ""

def test_status(wd):
    ok("new", "doc", cwd=wd)
    ok("insert", "doc", "--id", "k1", "--value", "hi", cwd=wd)
    r = ok("status", "doc", cwd=wd)
    low = r.stdout.lower()
    assert "elements: 1" in low
    assert "operations" in low

def test_persistence_across_invocations(wd):
    ok("new", "doc", cwd=wd)
    ok("insert", "doc", "--id", "persist", "--value", "durable", cwd=wd)
    r1 = ok("format", "doc", cwd=wd)
    # new process invocation should see same state
    r2 = ok("format", "doc", cwd=wd)
    assert r1.stdout == r2.stdout
    assert "durable" in r2.stdout

def test_empty_value(wd):
    ok("new", "doc", cwd=wd)
    ok("insert", "doc", "--id", "empty", "--value", "", cwd=wd)
    r = ok("get", "doc", "--id", "empty", cwd=wd)
    assert r.returncode == 0

def test_special_characters(wd):
    ok("new", "doc", cwd=wd)
    val = "Hello world — quotes ' \" and unicode café"
    ok("insert", "doc", "--id", "sp", "--value", val, cwd=wd)
    r = ok("get", "doc", "--id", "sp", cwd=wd)
    assert "Hello" in r.stdout

def test_many_operations(wd):
    ok("new", "doc", cwd=wd)
    for i in range(100):
        args = ["insert", "doc", "--id", f"m{i}", "--value", f"v{i}"]
        if i > 0:
            args += ["--after", f"m{i-1}"]
        ok(*args, cwd=wd)
    r = ok("status", "doc", cwd=wd)
    assert "elements: 100" in r.stdout.lower()

def test_combined_workflow(wd):
    ok("new", "doc", cwd=wd)
    ok("insert", "doc", "--id", "a", "--value", "Alpha", cwd=wd)
    ok("insert", "doc", "--id", "b", "--value", "Beta", "--after", "a", cwd=wd)
    ok("delete", "doc", "--id", "a", cwd=wd)
    ok("insert", "doc", "--id", "c", "--value", "Gamma", cwd=wd)
    r = ok("status", "doc", cwd=wd)
    assert "elements: 2" in r.stdout.lower()
    r = ok("format", "doc", cwd=wd)
    assert "Gamma" in r.stdout and "Beta" in r.stdout

def test_large_document(wd):
    ok("new", "doc", cwd=wd)
    for i in range(500):
        args = ["insert", "doc", "--id", f"lg{i}", "--value", f"val{i}"]
        if i > 0:
            args += ["--after", f"lg{i-1}"]
        ok(*args, cwd=wd)
    r = ok("status", "doc", cwd=wd)
    assert "elements: 500" in r.stdout.lower()

def test_idempotent_recovery(wd):
    ok("new", "doc", cwd=wd)
    ok("insert", "doc", "--id", "idem", "--value", "once", cwd=wd)
    a = ok("format", "doc", cwd=wd).stdout
    b = ok("format", "doc", cwd=wd).stdout
    assert a == b
    assert "once" in a
