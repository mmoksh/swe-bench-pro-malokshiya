"""Step 5 — Adversarial Hardening — strict suite (15 tests). Enforces Byzantine validation, WAL durability, CRDT convergence."""
import os, subprocess, tempfile, shutil, json, pathlib, random
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

def test_verify_healthy(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","v1","--value","ok",cwd=wd)
    r=ok("verify","doc",cwd=wd)
    assert "ok" in r.stdout.lower()
    assert r.returncode==0

def test_verify_detects_duplicate_order(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","dup","--value","A",cwd=wd)
    p=pathlib.Path(wd)/".collab-doc"/"doc.json"
    wal=pathlib.Path(wd)/".collab-doc"/"doc.wal"
    assert p.exists()
    # Remove WAL so corruption is not healed via replay — forces Byzantine detection
    if wal.exists():
        wal.unlink()
    data=json.load(open(p))
    data["order"]=["dup","dup"]
    json.dump(data, open(p,"w"))
    r=cli("verify","doc",cwd=wd)
    assert r.returncode!=0, "verify must detect duplicate order"
    txt=(r.stdout+r.stderr).lower()
    assert "duplicate" in txt or "corrupt" in txt

def test_verify_detects_missing_ref(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","m1","--value","A",cwd=wd)
    p=pathlib.Path(wd)/".collab-doc"/"doc.json"
    wal=pathlib.Path(wd)/".collab-doc"/"doc.wal"
    assert p.exists()
    if wal.exists():
        wal.unlink()
    data=json.load(open(p))
    data["order"].append("ghost999")
    json.dump(data, open(p,"w"))
    r=cli("verify","doc",cwd=wd)
    assert r.returncode!=0, f"verify must fail on missing ref, got 0 stdout={r.stdout} stderr={r.stderr}"
    txt=(r.stdout+r.stderr).lower()
    assert "ghost999" in txt or "missing" in txt or "corrupt" in txt

def test_path_traversal_blocked(wd):
    r=fail("new","../../tmp/evil",cwd=wd)
    assert "path" in r.stderr.lower() or "invalid" in r.stderr.lower() or "traversal" in r.stderr.lower() or "separator" in r.stderr.lower()
    fail("new","../evil",cwd=wd)
    fail("new","a/b",cwd=wd)
    assert not pathlib.Path("/tmp/evil.json").exists()
    assert not (pathlib.Path(wd)/".collab-doc"/"evil.json").exists()

def test_wal_corruption_handled(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","wc","--value","hi",cwd=wd)
    before=ok("format","doc",cwd=wd).stdout
    assert before.strip()=="hi"
    wal=pathlib.Path(wd)/".collab-doc"/"doc.wal"
    assert wal.exists()
    wal.write_text(wal.read_text()+"INVALID LINE\n{ not json\n")
    r=cli("status","doc",cwd=wd)
    assert r.returncode==0, f"status must succeed ignoring bad WAL lines, got {r.returncode} {r.stderr}"
    assert "panic" not in r.stderr.lower()
    assert "elements: 1" in r.stdout.lower()
    r2=cli("format","doc",cwd=wd)
    assert r2.returncode==0
    assert r2.stdout.strip()=="hi"
    assert "panic" not in r2.stderr.lower()
    # verify still healthy (bad lines skipped)
    r3=cli("verify","doc",cwd=wd)
    assert r3.returncode==0

def test_large_value(wd):
    ok("new","doc",cwd=wd)
    big="Z"*100_000
    ok("insert","doc","--id","big","--value",big,cwd=wd)
    r=ok("get","doc","--id","big",cwd=wd)
    assert r.stdout.strip()==big
    assert len(r.stdout.strip())==100_000

def test_many_clients(wd):
    ok("new","doc",cwd=wd)
    for i in range(20):
        ok("insert","doc","--id",f"mc{i}","--value",f"v{i}","--client",f"c{i}",cwd=wd)
    ok("merge","doc","--clients",",".join(f"c{i}" for i in range(20)),cwd=wd)
    r=ok("format","doc",cwd=wd)
    lines=[l for l in r.stdout.strip().splitlines() if l]
    assert len(lines)==20
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
    assert len([l for l in outs[0].strip().splitlines() if l])==91

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
    assert "A" in outs[0] and "E" in outs[0]

def test_special_chars_preserved(wd):
    ok("new","doc",cwd=wd)
    vals=["hello world","café — test","quote ' \" "]
    for i,val in enumerate(vals):
        ok("insert","doc","--id",f"sc{i}","--value",val,cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "hello world" in r.stdout
    assert "café" in r.stdout
    # get each preserves exact
    for i,val in enumerate(vals):
        r2=ok("get","doc","--id",f"sc{i}",cwd=wd)
        assert r2.stdout.strip()==val.strip()

def test_save_load_corrupted_snapshot(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","orig","--value","ok",cwd=wd)
    bad=os.path.join(wd,"bad.json")
    open(bad,"w").write("{ not json")
    r=fail("load","--path",bad,"--doc-id","bad2",cwd=wd)
    assert "corrupt" in r.stderr.lower() or "corrupt" in r.stdout.lower() or "invalid" in r.stderr.lower()
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
    assert len([l for l in before.strip().splitlines() if l])==25
    ok("gc","doc",cwd=wd)
    after=ok("format","doc",cwd=wd).stdout
    assert before==after
    assert cli("verify","doc",cwd=wd).returncode==0

def test_verify_after_gc(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","vg","--value","x",cwd=wd)
    ok("delete","doc","--id","vg",cwd=wd)
    ok("gc","doc",cwd=wd)
    r=ok("verify","doc",cwd=wd)
    assert "ok" in r.stdout.lower()
    assert "elements: 0" in r.stdout.lower()

def test_idempotent_ops_during_storm(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","idem","--value","once",cwd=wd)
    r=fail("insert","doc","--id","idem","--value","again",cwd=wd)
    assert "duplicate" in r.stderr.lower() or "already" in r.stderr.lower()
    assert ok("format","doc",cwd=wd).stdout.strip()=="once"

def test_undo_redo_under_concurrency(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","ua","--value","A","--client","alice",cwd=wd)
    ok("insert","doc","--id","ub","--value","B","--client","bob",cwd=wd)
    ok("undo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert r.stdout.strip()=="B"
    ok("redo","doc","--client","alice",cwd=wd)
    r=ok("format","doc",cwd=wd)
    lines=r.stdout.strip().splitlines()
    assert "A" in lines and "B" in lines
    assert len(lines)==2
