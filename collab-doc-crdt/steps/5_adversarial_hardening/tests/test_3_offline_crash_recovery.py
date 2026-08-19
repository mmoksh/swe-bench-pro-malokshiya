"""Step 3 — Offline + Crash Recovery — fresh suite (11 tests)."""
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

def test_save_creates_file(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","sv1","--value","data",cwd=wd)
    snap=os.path.join(wd,"out.json")
    ok("save","doc","--path",snap,cwd=wd)
    assert os.path.exists(snap)
    assert json.load(open(snap)) is not None

def test_load_recreates(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","a","--value","alpha",cwd=wd)
    ok("insert","doc","--id","b","--value","beta","--after","a",cwd=wd)
    snap=os.path.join(wd,"s.json")
    ok("save","doc","--path",snap,cwd=wd)
    ok("load","--path",snap,"--doc-id","copy",cwd=wd)
    r=ok("format","copy",cwd=wd)
    assert "alpha" in r.stdout and "beta" in r.stdout

def test_save_load_roundtrip(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","r1","--value","one","--client","alice",cwd=wd)
    ok("insert","doc","--id","r2","--value","two","--client","bob","--after","r1",cwd=wd)
    snap=os.path.join(wd,"rt.json")
    ok("save","doc","--path",snap,cwd=wd)
    before=ok("format","doc",cwd=wd).stdout
    ok("load","--path",snap,"--doc-id","rt",cwd=wd)
    after=ok("format","rt",cwd=wd).stdout
    assert before==after

def test_save_load_preserves_status(wd):
    ok("new","doc",cwd=wd)
    for i in range(5):
        ok("insert","doc","--id",f"ss{i}","--value",f"v{i}",cwd=wd)
    snap=os.path.join(wd,"st.json")
    ok("save","doc","--path",snap,cwd=wd)
    ok("load","--path",snap,"--doc-id","rt2",cwd=wd)
    r=ok("status","rt2",cwd=wd)
    assert "elements: 5" in r.stdout.lower()

def test_save_nonexistent_fails(wd):
    fail("save","ghost","--path",os.path.join(wd,"x.json"),cwd=wd)

def test_load_nonexistent_fails(wd):
    fail("load","--path","/no/such/file.json","--doc-id","d",cwd=wd)

def test_wal_exists_after_ops(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","w1","--value","wal",cwd=wd)
    # at least one persistence artifact should exist
    base=pathlib.Path(wd)/".collab-doc"
    assert (base/"doc.json").exists() or (base/"doc.wal").exists()

def test_wal_recovery_on_truncation(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","t1","--value","A",cwd=wd)
    ok("insert","doc","--id","t2","--value","B","--after","t1",cwd=wd)
    p=pathlib.Path(wd)/".collab-doc"/"doc.json"
    if p.exists():
        p.write_text("{ broken json")
        r=cli("status","doc",cwd=wd)
        assert r.returncode in [0,1]
        # should not segfault/crash hard
        assert "panic" not in r.stderr.lower()

def test_large_save_load(wd):
    ok("new","doc",cwd=wd)
    for i in range(200):
        args=["insert","doc","--id",f"ls{i}","--value",f"vv{i}"]
        if i>0: args+=["--after",f"ls{i-1}"]
        ok(*args,cwd=wd)
    snap=os.path.join(wd,"large.json")
    ok("save","doc","--path",snap,cwd=wd)
    ok("load","--path",snap,"--doc-id","large2",cwd=wd)
    r=ok("status","large2",cwd=wd)
    assert "elements: 200" in r.stdout.lower()

def test_save_load_preserves_clients(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","ca","--value","hi","--client","alice",cwd=wd)
    ok("insert","doc","--id","cb","--value","yo","--client","bob",cwd=wd)
    snap=os.path.join(wd,"cl.json")
    ok("save","doc","--path",snap,cwd=wd)
    ok("load","--path",snap,"--doc-id","cl2",cwd=wd)
    r=ok("status","cl2",cwd=wd)
    assert "client" in r.stdout.lower()

def test_atomic_write_no_corruption_parallel(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","a1","--value","one",cwd=wd)
    ok("insert","doc","--id","a2","--value","two",cwd=wd)
    p=pathlib.Path(wd)/".collab-doc"/"doc.json"
    if p.exists():
        assert json.load(open(p)) is not None
    ok("format","doc",cwd=wd)
