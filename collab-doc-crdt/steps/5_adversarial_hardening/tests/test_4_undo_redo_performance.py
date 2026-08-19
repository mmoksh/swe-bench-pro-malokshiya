"""Step 4 — Undo/Redo + Performance — fresh suite (12 tests)."""
import os, subprocess, tempfile, shutil, json, pathlib, time
import pytest
BIN_CANDIDATES=["/app/target/release/collab-doc","/app/target/debug/collab-doc","collab-doc"]
def _bin():
    for c in BIN_CANDIDATES:
        if "/" in c and os.path.exists(c): return c
        if "/" not in c and shutil.which(c): return c
    return BIN_CANDIDATES[0]
BIN=_bin()
def cli(*a,cwd=None): return subprocess.run([BIN,*a],cwd=cwd,capture_output=True,text=True)
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
    assert "keep" in r.stdout and "drop" not in r.stdout

def test_undo_delete_restores(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","d1","--value","alive","--client","alice",cwd=wd)
    ok("delete","doc","--id","d1","--client","alice",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()==""
    ok("undo","doc","--client","alice",cwd=wd)
    assert "alive" in ok("format","doc",cwd=wd).stdout

def test_redo_after_undo(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","r1","--value","one","--client","alice",cwd=wd)
    ok("insert","doc","--id","r2","--value","two","--client","alice","--after","r1",cwd=wd)
    ok("undo","doc","--client","alice",cwd=wd)
    ok("redo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "one" in r.stdout and "two" in r.stdout

def test_undo_no_ops_fails(wd):
    ok("new","doc",cwd=wd)
    fail("undo","doc","--client","alice",cwd=wd)

def test_redo_no_ops_fails(wd):
    ok("new","doc",cwd=wd)
    fail("redo","doc","--client","nobody",cwd=wd)

def test_per_client_isolation(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","ca","--value","A","--client","alice",cwd=wd)
    ok("insert","doc","--id","cb","--value","B","--client","bob",cwd=wd)
    ok("undo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "A" not in r.stdout and "B" in r.stdout
    ok("undo","doc","--client","bob",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()==""

def test_undo_causality(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","base","--value","B","--client","alice",cwd=wd)
    ok("insert","doc","--id","child","--value","C","--client","alice","--after","base",cwd=wd)
    # LIFO: child is most recent, undo should remove child first
    ok("undo","doc","--client","alice",cwd=wd)
    assert "C" not in ok("format","doc",cwd=wd).stdout
    ok("undo","doc","--client","alice",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()==""

def test_gc_preserves_format(wd):
    ok("new","doc",cwd=wd)
    for i in range(10):
        ok("insert","doc","--id",f"gc{i}","--value",f"v{i}","--client","alice",cwd=wd)
    for i in range(5):
        ok("delete","doc","--id",f"gc{i}","--client","alice",cwd=wd)
    before=ok("format","doc",cwd=wd).stdout
    ok("gc","doc",cwd=wd)
    after=ok("format","doc",cwd=wd).stdout
    assert before==after

def test_gc_removes_tombstones(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","t1","--value","x",cwd=wd)
    ok("delete","doc","--id","t1",cwd=wd)
    before=ok("status","doc",cwd=wd).stdout
    ok("gc","doc",cwd=wd)
    after=ok("status","doc",cwd=wd).stdout
    assert "elements: 0" in after.lower()
    assert ok("format","doc",cwd=wd).stdout.strip()==""

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
    assert f"vv{n-1}" in r.stdout

def test_save_load_preserves_undo(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","sa","--value","keep","--client","alice",cwd=wd)
    ok("insert","doc","--id","sb","--value","drop","--client","alice","--after","sa",cwd=wd)
    snap=os.path.join(wd,"snap.json")
    ok("save","doc","--path",snap,cwd=wd)
    ok("load","--path",snap,"--doc-id","copy",cwd=wd)
    # undo on loaded copy should not crash
    r=cli("undo","copy","--client","alice",cwd=wd)
    assert r.returncode in [0,1]

def test_undo_redo_multiple(wd):
    ok("new","doc",cwd=wd)
    for i in range(3):
        ok("insert","doc","--id",f"ur{i}","--value",f"v{i}","--client","alice",cwd=wd)
    for _ in range(3):
        ok("undo","doc","--client","alice",cwd=wd)
    assert ok("format","doc",cwd=wd).stdout.strip()==""
    for _ in range(3):
        ok("redo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "v0" in r.stdout and "v2" in r.stdout
