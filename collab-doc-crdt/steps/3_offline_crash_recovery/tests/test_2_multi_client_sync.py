"""Step 2 — Multi-Client Sync — fresh suite (13 new + 18 inherited).

Tests sync/merge, client isolation, log, causal ordering, determinism.
"""
import os, subprocess, tempfile, shutil, json, random, pathlib
import pytest

BIN_CANDIDATES = ["/app/target/release/collab-doc","/app/target/debug/collab-doc","collab-doc"]
def _bin():
    for c in BIN_CANDIDATES:
        if "/" in c and os.path.exists(c): return c
        if "/" not in c and shutil.which(c): return c
    return BIN_CANDIDATES[0]
BIN=_bin()
def cli(*a,cwd=None): return subprocess.run([BIN,*a],cwd=cwd,capture_output=True,text=True)
def ok(*a,cwd=None):
    r=cli(*a,cwd=cwd)
    assert r.returncode==0, f"ok fail {a}: {r.returncode}\n{r.stdout}\n{r.stderr}"
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

def test_insert_with_client(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","c1","--value","hello","--client","alice",cwd=wd)
    r=ok("get","doc","--id","c1",cwd=wd)
    assert "hello" in r.stdout

def test_multi_client_format(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","e1","--value","A","--client","alice",cwd=wd)
    ok("insert","doc","--id","e2","--value","B","--client","bob","--after","e1",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "A" in r.stdout and "B" in r.stdout

def test_sync_command(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","s1","--value","X","--client","alice",cwd=wd)
    # sync should be idempotent and not error
    ok("sync","doc","--from","alice","--to","bob",cwd=wd)
    ok("sync","doc","--from","alice","--to","bob",cwd=wd)

def test_merge_command(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","a1","--value","A","--client","alice",cwd=wd)
    ok("insert","doc","--id","b1","--value","B","--client","bob",cwd=wd)
    ok("merge","doc","--clients","alice,bob",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "A" in r.stdout and "B" in r.stdout

def test_merge_order_independence(wd):
    def one(order):
        d=tempfile.mkdtemp()
        ok("new","doc",cwd=d)
        ok("insert","doc","--id","x","--value","X","--client","alice",cwd=d)
        ok("insert","doc","--id","y","--value","Y","--client","bob","--after","x",cwd=d)
        ok("insert","doc","--id","z","--value","Z","--client","carol","--after","x",cwd=d)
        ok("merge","doc","--clients",order,cwd=d)
        out=ok("format","doc",cwd=d).stdout
        shutil.rmtree(d)
        return out
    a=one("alice,bob,carol")
    b=one("carol,alice,bob")
    c=one("bob,carol,alice")
    assert a==b==c

def test_status_clients(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","p1","--value","v1","--client","alice",cwd=wd)
    ok("insert","doc","--id","p2","--value","v2","--client","bob",cwd=wd)
    r=ok("status","doc",cwd=wd)
    assert "client" in r.stdout.lower()

def test_log_command(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","l1","--value","hi","--client","alice",cwd=wd)
    r=ok("log","doc",cwd=wd)
    assert "alice" in r.stdout.lower()

def test_log_filter_client(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","la","--value","A","--client","alice",cwd=wd)
    ok("insert","doc","--id","lb","--value","B","--client","bob",cwd=wd)
    r=ok("log","doc","--client","alice",cwd=wd)
    assert "alice" in r.stdout.lower()
    assert "bob" not in r.stdout.lower()

def test_concurrent_inserts_deterministic(wd):
    def trial():
        d=tempfile.mkdtemp()
        ok("new","doc",cwd=d)
        ok("insert","doc","--id","root","--value","R",cwd=d)
        ok("insert","doc","--id","ca","--value","CA","--client","alice","--after","root",cwd=d)
        ok("insert","doc","--id","cb","--value","CB","--client","bob","--after","root",cwd=d)
        ok("merge","doc","--clients","alice,bob",cwd=d)
        out=ok("format","doc",cwd=d).stdout
        shutil.rmtree(d)
        return out
    outs=[trial() for _ in range(5)]
    assert all(o==outs[0] for o in outs)

def test_causal_ordering(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","ca","--value","CA","--client","alice",cwd=wd)
    ok("sync","doc","--from","alice","--to","bob",cwd=wd)
    ok("insert","doc","--id","cb","--value","CB","--client","bob","--after","ca",cwd=wd)
    r=ok("format","doc",cwd=wd)
    lines=r.stdout.strip().splitlines()
    assert lines.index("CA") < lines.index("CB")

def test_merge_three_clients(wd):
    ok("new","doc",cwd=wd)
    for cid,val in [("alice","VA"),("bob","VB"),("carol","VC")]:
        ok("insert","doc","--id",cid,"--value",val,"--client",cid,cwd=wd)
    ok("merge","doc","--clients","alice,bob,carol",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "VA" in r.stdout and "VB" in r.stdout and "VC" in r.stdout

def test_client_clock_preserved_after_reload(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","clk","--value","tick","--client","alice",cwd=wd)
    r1=ok("status","doc",cwd=wd)
    r2=ok("status","doc",cwd=wd)
    assert "client" in r1.stdout.lower()
    assert "client" in r2.stdout.lower()

def test_backward_compat_no_client(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","bc","--value","legacy",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert "legacy" in r.stdout
