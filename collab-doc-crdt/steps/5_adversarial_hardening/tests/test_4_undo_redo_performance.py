"""Step 4 — Undo/Redo + Performance — strict suite (12 tests)."""
import os, subprocess, tempfile, shutil, pathlib, time
import pytest
BIN_CANDIDATES=["/app/target/debug/collab-doc","/app/target/release/collab-doc","collab-doc"]
def _bin():
    for c in BIN_CANDIDATES:
        if "/" in c and os.path.exists(c): return c
        if "/" not in c and shutil.which(c): return c
    return BIN_CANDIDATES[0]
BIN=_bin()
def _resolve_bin():
    for c in BIN_CANDIDATES:
        if "/" in c and __import__('os').path.exists(c): return c
        if "/" not in c and __import__('shutil').which(c): return c
    return BIN
def cli(*a,cwd=None):
    b=_resolve_bin()
    return __import__('subprocess').run([b,*a],cwd=cwd,capture_output=True,text=True)
def ok(*a,cwd=None):
    r=cli(*a,cwd=cwd)
    assert r.returncode==0, f"ok fail {a}: {r.stdout}\n{r.stderr}"
    return r
def fail(*a,cwd=None):
    r=cli(*a,cwd=cwd)
    assert r.returncode!=0, f"expected fail {a}"
    return r
@pytest.fixture
def wd():
    d=tempfile.mkdtemp()
    yield d
    shutil.rmtree(d,ignore_errors=True)

def test_undo_insert(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","u1","--value","keep","--client","alice",cwd=wd)
    ok("insert","doc","--id","u2","--value","drop","--client","alice","--after","u1",cwd=wd)
    ok("undo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert r.stdout.strip()=="keep"

def test_undo_delete_restores(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","d1","--value","alive","--client","alice",cwd=wd)
    ok("delete","doc","--id","d1","--client","alice",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()==""
    ok("undo","doc","--client","alice",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()=="alive"

def test_redo_after_undo(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","r1","--value","one","--client","alice",cwd=wd)
    ok("insert","doc","--id","r2","--value","two","--client","alice","--after","r1",cwd=wd)
    ok("undo","doc","--client","alice",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()=="one"
    ok("redo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert r.stdout.strip().splitlines()==["one","two"]

def test_undo_no_ops_fails(wd):
    ok("new","doc",cwd=wd)
    r=fail("undo","doc","--client","alice",cwd=wd)
    assert "nothing" in r.stderr.lower() or "undo" in r.stderr.lower() or "error" in r.stderr.lower()

def test_redo_no_ops_fails(wd):
    ok("new","doc",cwd=wd)
    r=fail("redo","doc","--client","nobody",cwd=wd)
    assert "nothing" in r.stderr.lower() or "redo" in r.stderr.lower() or "error" in r.stderr.lower()

def test_per_client_isolation(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","ca","--value","A","--client","alice",cwd=wd)
    ok("insert","doc","--id","cb","--value","B","--client","bob",cwd=wd)
    ok("undo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert r.stdout.strip()=="B"
    ok("undo","doc","--client","bob",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()==""

def test_undo_causality(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","base","--value","B","--client","alice",cwd=wd)
    ok("insert","doc","--id","child","--value","C","--client","alice","--after","base",cwd=wd)
    ok("undo","doc","--client","alice",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()=="B"
    ok("undo","doc","--client","alice",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()==""

def test_gc_preserves_format(wd):
    ok("new","doc",cwd=wd)
    for i in range(10):
        ok("insert","doc","--id",f"gc{i}","--value",f"v{i}","--client","alice",cwd=wd)
    for i in range(5):
        ok("delete","doc","--id",f"gc{i}","--client","alice",cwd=wd)
    before=ok("format","doc",cwd=wd).stdout
    assert len([l for l in before.strip().splitlines() if l])==5
    ok("gc","doc",cwd=wd)
    after=ok("format","doc",cwd=wd).stdout
    assert before==after

def test_gc_removes_tombstones(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","t1","--value","x",cwd=wd)
    ok("delete","doc","--id","t1",cwd=wd)
    ok("gc","doc",cwd=wd)
    after=ok("status","doc",cwd=wd).stdout
    assert "elements: 0" in after.lower()
    assert ok("format","doc",cwd=wd).stdout.strip()==""
    # after GC verify still healthy
    assert cli("verify","doc",cwd=wd).returncode==0

def test_large_doc_performance(wd):
    ok("new","doc",cwd=wd)
    n=1000
    t0=time.time()
    for i in range(n):
        args=["insert","doc","--id",f"perf{i}","--value",f"vv{i}"]
        if i>0: args+=["--after",f"perf{i-1}"]
        ok(*args,cwd=wd)
    assert time.time()-t0 < 90, "insert 1000 too slow"
    t0=time.time()
    r=ok("format","doc",cwd=wd)
    assert time.time()-t0 < 2
    assert "vv0" in r.stdout and f"vv{n-1}" in r.stdout
    r2=ok("status","doc",cwd=wd)
    assert "elements: 1000" in r2.stdout.lower()

def test_save_load_preserves_undo(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","sa","--value","keep","--client","alice",cwd=wd)
    ok("insert","doc","--id","sb","--value","drop","--client","alice","--after","sa",cwd=wd)
    snap=os.path.join(wd,"snap.json")
    ok("save","doc","--path",snap,cwd=wd)
    ok("load","--path",snap,"--doc-id","copy",cwd=wd)
    # strict: undo must succeed and remove drop
    r=cli("undo","copy","--client","alice",cwd=wd)
    assert r.returncode==0, f"undo after load should succeed, got {r.returncode} {r.stderr}"
    assert "panic" not in r.stderr.lower()
    r2=ok("format","copy",cwd=wd)
    assert r2.stdout.strip()=="keep"
    # redo must restore
    ok("redo","copy","--client","alice",cwd=wd)
    r3=ok("format","copy",cwd=wd)
    assert r3.stdout.strip().splitlines()==["keep","drop"]

def test_undo_redo_multiple(wd):
    ok("new","doc",cwd=wd)
    for i in range(3):
        ok("insert","doc","--id",f"ur{i}","--value",f"v{i}","--client","alice",cwd=wd)
    for _ in range(3):
        ok("undo","doc","--client","alice",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()==""
    # extra undo must fail
    fail("undo","doc","--client","alice",cwd=wd)
    for _ in range(3):
        ok("redo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert r.stdout.strip().splitlines()==["v2","v1","v0"]  # fixed: insert without --after goes to head per spec
    fail("redo","doc","--client","alice",cwd=wd)
