"""Step 3 — Offline + Crash Recovery — strict suite (11 tests). Enforces WAL durability."""
import os, subprocess, tempfile, shutil, json, pathlib
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

def test_save_creates_file(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","sv1","--value","data",cwd=wd)
    snap=os.path.join(wd,"out.json")
    ok("save","doc","--path",snap,cwd=wd)
    assert os.path.exists(snap)
    data=json.load(open(snap))
    assert data["name"]=="doc"
    assert "elements" in data or "order" in data

def test_load_recreates(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","a","--value","alpha",cwd=wd)
    ok("insert","doc","--id","b","--value","beta","--after","a",cwd=wd)
    snap=os.path.join(wd,"s.json")
    ok("save","doc","--path",snap,cwd=wd)
    ok("load","--path",snap,"--doc-id","copy",cwd=wd)
    r=ok("format","copy",cwd=wd)
    assert r.stdout.strip().splitlines()==["alpha","beta"]

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
    assert before.strip().splitlines()==["one","two"]

def test_save_load_preserves_status(wd):
    ok("new","doc",cwd=wd)
    for i in range(5):
        ok("insert","doc","--id",f"ss{i}","--value",f"v{i}",cwd=wd)
    snap=os.path.join(wd,"st.json")
    ok("save","doc","--path",snap,cwd=wd)
    ok("load","--path",snap,"--doc-id","rt2",cwd=wd)
    r=ok("status","rt2",cwd=wd)
    assert "elements: 5" in r.stdout.lower()
    assert "operations: 5" in r.stdout.lower()

def test_save_nonexistent_fails(wd):
    r=fail("save","ghost","--path",os.path.join(wd,"x.json"),cwd=wd)
    assert "not found" in r.stderr.lower() or "not found" in r.stdout.lower() or "error" in r.stderr.lower()

def test_load_nonexistent_fails(wd):
    r=fail("load","--path","/no/such/file.json","--doc-id","d",cwd=wd)
    assert "not found" in r.stderr.lower() or "not found" in r.stdout.lower() or "error" in r.stderr.lower()

def test_wal_exists_after_ops(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","w1","--value","wal",cwd=wd)
    base=pathlib.Path(wd)/".collab-doc"
    assert (base/"doc.json").exists()
    assert (base/"doc.wal").exists()
    # wal must contain the operation
    wal_text=(base/"doc.wal").read_text()
    assert "w1" in wal_text
    # json must be valid
    assert json.load(open(base/"doc.json")) is not None

def test_wal_recovery_on_truncation(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","t1","--value","A",cwd=wd)
    ok("insert","doc","--id","t2","--value","B","--after","t1",cwd=wd)
    before=ok("format","doc",cwd=wd).stdout
    assert before.strip().splitlines()==["A","B"]
    p=pathlib.Path(wd)/".collab-doc"/"doc.json"
    assert p.exists()
    # WAL must exist for recovery to be possible
    wal=pathlib.Path(wd)/".collab-doc"/"doc.wal"
    assert wal.exists()
    p.write_text("{ broken json")
    r=cli("status","doc",cwd=wd)
    assert r.returncode==0, f"status should recover from WAL, got {r.returncode} stderr={r.stderr}"
    assert "panic" not in r.stderr.lower()
    # must recover both elements via WAL
    r2=cli("format","doc",cwd=wd)
    assert r2.returncode==0
    assert r2.stdout==before
    assert "A" in r2.stdout and "B" in r2.stdout
    # verify after recovery is healthy
    r3=cli("verify","doc",cwd=wd)
    assert r3.returncode==0

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
    r2=ok("format","large2",cwd=wd)
    assert "vv0" in r2.stdout and "vv199" in r2.stdout
    assert len([l for l in r2.stdout.strip().splitlines() if l])==200

def test_save_load_preserves_clients(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","ca","--value","hi","--client","alice",cwd=wd)
    ok("insert","doc","--id","cb","--value","yo","--client","bob",cwd=wd)
    snap=os.path.join(wd,"cl.json")
    ok("save","doc","--path",snap,cwd=wd)
    ok("load","--path",snap,"--doc-id","cl2",cwd=wd)
    r=ok("status","cl2",cwd=wd)
    low=r.stdout.lower()
    assert "alice" in low and "bob" in low
    r2=ok("log","cl2",cwd=wd)
    assert "alice" in r2.stdout.lower() and "bob" in r2.stdout.lower()

def test_atomic_write_no_corruption_parallel(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","a1","--value","one",cwd=wd)
    ok("insert","doc","--id","a2","--value","two",cwd=wd)
    p=pathlib.Path(wd)/".collab-doc"/"doc.json"
    assert p.exists()
    data=json.load(open(p))
    assert data is not None
    assert "order" in data and "elements" in data
    r=ok("format","doc",cwd=wd)
    assert r.returncode==0
    assert "one" in r.stdout or "two" in r.stdout
