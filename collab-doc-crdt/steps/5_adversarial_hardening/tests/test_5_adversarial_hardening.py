"""Step 5 — Adversarial Hardening — fresh suite (15 tests)."""
import os, subprocess, tempfile, shutil, json, pathlib, time, random
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

def test_verify_healthy(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","v1","--value","ok",cwd=wd)
    r=ok("verify","doc",cwd=wd)
    assert r.returncode==0

def test_verify_detects_duplicate_order(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","dup","--value","A",cwd=wd)
    p=pathlib.Path(wd)/".collab-doc"/"doc.json"
    if p.exists():
        data=json.load(open(p))
        data["order"]=["dup","dup"]
        json.dump(data, open(p,"w"))
        r=cli("verify","doc",cwd=wd)
        txt=(r.stdout+r.stderr).lower()
        assert r.returncode!=0 or "corrupt" in txt or "duplicate" in txt

def test_verify_detects_missing_ref(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","m1","--value","A",cwd=wd)
    p=pathlib.Path(wd)/".collab-doc"/"doc.json"
    if p.exists():
        data=json.load(open(p))
        data["order"].append("ghost999")
        json.dump(data, open(p,"w"))
        r=cli("verify","doc",cwd=wd)
        # either verify fails, or graceful handling via filtered format
        if r.returncode==0:
            r2=cli("format","doc",cwd=wd)
            # ghost must not appear, or command should error
            assert "ghost999" not in r2.stdout or r2.returncode!=0

def test_path_traversal_blocked(wd):
    fail("new","../../tmp/evil",cwd=wd)
    fail("new","../evil",cwd=wd)
    fail("new","a/b",cwd=wd)
    assert not pathlib.Path("/tmp/evil.json").exists()

def test_wal_corruption_handled(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","wc","--value","hi",cwd=wd)
    wal=pathlib.Path(wd)/".collab-doc"/"doc.wal"
    if wal.exists():
        wal.write_text(wal.read_text()+"INVALID LINE\n{ not json\n")
        r=cli("status","doc",cwd=wd)
        assert r.returncode in [0,1]
        assert "panic" not in r.stderr.lower()
        r=cli("format","doc",cwd=wd)
        assert r.returncode in [0,1]

def test_large_value(wd):
    ok("new","doc",cwd=wd)
    big="Z"*100_000
    ok("insert","doc","--id","big","--value",big,cwd=wd)
    r=ok("get","doc","--id","big",cwd=wd)
    # stdout may contain newline; count chars via stripping
    assert len(r.stdout.strip())==100_000

def test_many_clients(wd):
    ok("new","doc",cwd=wd)
    for i in range(20):
        ok("insert","doc","--id",f"mc{i}","--value",f"v{i}","--client",f"c{i}",cwd=wd)
    ok("merge","doc","--clients",",".join(f"c{i}" for i in range(20)),cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "v0" in r.stdout and "v19" in r.stdout

def test_concurrent_storm_deterministic(wd):
    def storm():
        d=tempfile.mkdtemp()
        ok("new","doc",cwd=d)
        ok("insert","doc","--id","root","--value","R",cwd=d)
        ops=[(f"u{i%3}",f"e{i}",f"v{i}") for i in range(90)]
        random.seed(42)
        shuffled=ops[:]
        random.shuffle(shuffled)
        for client,eid,val in shuffled:
            ok("insert","doc","--id",eid,"--value",val,"--client",client,"--after","root",cwd=d)
        ok("merge","doc","--clients","u0,u1,u2",cwd=d)
        out=ok("format","doc",cwd=d).stdout
        shutil.rmtree(d)
        return out
    outs=[storm() for _ in range(3)]
    assert outs[0]==outs[1]==outs[2]

def test_determinism_random_apply_order(wd):
    seq=[("alice","a","A",None),("bob","b","B","a"),("carol","c","C","a"),("alice","d","D","b"),("bob","e","E","c")]
    def apply(order):
        d=tempfile.mkdtemp()
        ok("new","doc",cwd=d)
        pending=[seq[i] for i in order]
        attempts=0
        max_attempts = len(pending)*5 + 10
        while pending and attempts < max_attempts:
            cid,eid,val,after=pending.pop(0)
            args=["insert","doc","--id",eid,"--value",val,"--client",cid]
            if after: args+=["--after",after]
            r=cli(*args,cwd=d)
            if r.returncode!=0 and "after" in r.stderr.lower():
                pending.append((cid,eid,val,after))
            else:
                assert r.returncode==0, r.stderr
            attempts+=1
        assert not pending, f"pending {pending} after {attempts} attempts" 
        ok("merge","doc","--clients","alice,bob,carol",cwd=d)
        out=ok("format","doc",cwd=d).stdout
        shutil.rmtree(d)
        return out
    orders=[]
    for _ in range(5):
        o=list(range(5))
        random.shuffle(o)
        orders.append(o)
    random.seed(9)
    outs=[apply(o) for o in orders]
    assert all(o==outs[0] for o in outs)

def test_special_chars_preserved(wd):
    ok("new","doc",cwd=wd)
    for i,val in enumerate(["hello world","café — test","quote ' \" "]):
        ok("insert","doc","--id",f"sc{i}","--value",val,cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "hello world" in r.stdout

def test_save_load_corrupted_snapshot(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","orig","--value","ok",cwd=wd)
    bad=os.path.join(wd,"bad.json")
    open(bad,"w").write("{ not json")
    fail("load","--path",bad,"--doc-id","bad2",cwd=wd)
    assert "ok" in ok("format","doc",cwd=wd).stdout

def test_gc_safety_under_load(wd):
    ok("new","doc",cwd=wd)
    for i in range(50):
        args=["insert","doc","--id",f"gc{i}","--value",f"v{i}"]
        if i>0: args+=["--after",f"gc{i-1}"]
        ok(*args,cwd=wd)
    for i in range(0,50,2):
        ok("delete","doc","--id",f"gc{i}",cwd=wd)
    before=ok("format","doc",cwd=wd).stdout
    ok("gc","doc",cwd=wd)
    after=ok("format","doc",cwd=wd).stdout
    assert before==after

def test_verify_after_gc(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","vg","--value","x",cwd=wd)
    ok("delete","doc","--id","vg",cwd=wd)
    ok("gc","doc",cwd=wd)
    ok("verify","doc",cwd=wd)

def test_idempotent_ops_during_storm(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","idem","--value","once",cwd=wd)
    fail("insert","doc","--id","idem","--value","again",cwd=wd)
    assert "once" in ok("format","doc",cwd=wd).stdout

def test_undo_redo_under_concurrency(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","ua","--value","A","--client","alice",cwd=wd)
    ok("insert","doc","--id","ub","--value","B","--client","bob",cwd=wd)
    ok("undo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "A" not in r.stdout and "B" in r.stdout
    ok("redo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "A" in r.stdout and "B" in r.stdout
