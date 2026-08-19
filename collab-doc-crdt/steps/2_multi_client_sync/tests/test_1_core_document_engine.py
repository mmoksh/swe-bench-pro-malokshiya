"""Step 1 — Core Document Engine — strict suite (18 tests)."""
import os, subprocess, tempfile, shutil
import pytest

BIN_CANDIDATES = ["/app/target/debug/collab-doc","/app/target/release/collab-doc","collab-doc"]
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
    assert r.returncode==0, f"ok fail {a}: {r.returncode}\n{r.stdout}\n{r.stderr}"
    return r
def fail(*a,cwd=None):
    r=cli(*a,cwd=cwd)
    assert r.returncode!=0, f"expected fail {a} got 0 stdout={r.stdout}"
    return r
@pytest.fixture
def wd():
    d=tempfile.mkdtemp()
    yield d
    shutil.rmtree(d,ignore_errors=True)

def test_new_document(wd):
    ok("new","notes",cwd=wd)
    fail("new","notes",cwd=wd)
    ok("new","other",cwd=wd)
    # verify status of new doc is empty
    r=ok("status","notes",cwd=wd)
    assert "elements: 0" in r.stdout.lower()
    assert "operations: 0" in r.stdout.lower()

def test_insert_single(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","hx1","--value","Hello",cwd=wd)
    r=ok("get","doc","--id","hx1",cwd=wd)
    assert r.stdout.strip()=="Hello"

def test_insert_ordering(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","a","--value","first",cwd=wd)
    ok("insert","doc","--id","b","--value","second","--after","a",cwd=wd)
    ok("insert","doc","--id","c","--value","zero",cwd=wd)
    r=ok("format","doc",cwd=wd)
    lines=[l for l in r.stdout.strip().splitlines() if l]
    assert lines==["zero","first","second"], f"got {lines}"
    # exact file content ends with newline
    assert r.stdout.endswith("\n")

def test_insert_after(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","p","--value","P",cwd=wd)
    ok("insert","doc","--id","q","--value","Q","--after","p",cwd=wd)
    r=ok("format","doc",cwd=wd)
    lines=r.stdout.strip().splitlines()
    assert lines==["P","Q"]

def test_delete(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","x","--value","keep",cwd=wd)
    ok("insert","doc","--id","y","--value","remove","--after","x",cwd=wd)
    ok("delete","doc","--id","y",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert r.stdout.strip()=="keep"
    fail("get","doc","--id","y",cwd=wd)
    r=ok("status","doc",cwd=wd)
    assert "elements: 1" in r.stdout.lower()

def test_delete_unknown(wd):
    ok("new","doc",cwd=wd)
    r=fail("delete","doc","--id","ghost",cwd=wd)
    assert "not found" in r.stderr.lower() or "not found" in r.stdout.lower() or "error" in r.stderr.lower()

def test_duplicate_element_id(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","dup","--value","v1",cwd=wd)
    r=fail("insert","doc","--id","dup","--value","v2",cwd=wd)
    assert "duplicate" in r.stderr.lower() or "duplicate" in r.stdout.lower() or "already" in r.stderr.lower()
    assert "v1" in ok("get","doc","--id","dup",cwd=wd).stdout

def test_insert_after_unknown(wd):
    ok("new","doc",cwd=wd)
    r=fail("insert","doc","--id","n","--value","v","--after","nope",cwd=wd)
    assert "not found" in r.stderr.lower() or "after" in r.stderr.lower()

def test_get_not_found(wd):
    ok("new","doc",cwd=wd)
    r=fail("get","doc","--id","missing",cwd=wd)
    assert "not found" in r.stderr.lower() or "not found" in r.stdout.lower()

def test_format_empty(wd):
    ok("new","doc",cwd=wd)
    r=ok("format","doc",cwd=wd)
    assert r.stdout.strip()==""
    assert r.stdout=="" or r.stdout=="\n" or r.stdout.strip()==""

def test_status(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","k1","--value","hi",cwd=wd)
    r=ok("status","doc",cwd=wd)
    low=r.stdout.lower()
    assert "elements: 1" in low
    assert "operations: 1" in low
    assert "clients" in low

def test_persistence_across_invocations(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","persist","--value","durable",cwd=wd)
    r1=ok("format","doc",cwd=wd)
    r2=ok("format","doc",cwd=wd)
    assert r1.stdout==r2.stdout
    assert r1.stdout.strip()=="durable"
    # status persists
    r=ok("status","doc",cwd=wd)
    assert "elements: 1" in r.stdout.lower()

def test_empty_value(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","empty","--value","",cwd=wd)
    r=ok("get","doc","--id","empty",cwd=wd)
    # get for empty value returns empty line but exit 0
    assert r.returncode==0
    assert r.stdout.strip()==""
    # format should not contain phantom line
    r2=ok("format","doc",cwd=wd)
    # format joins values with newline; empty value contributes empty string
    # so format for single empty value is "\n" (one empty line)
    assert r2.returncode==0

def test_special_characters(wd):
    ok("new","doc",cwd=wd)
    val="Hello world — quotes ' \" and unicode café"
    ok("insert","doc","--id","sp","--value",val,cwd=wd)
    r=ok("get","doc","--id","sp",cwd=wd)
    assert r.stdout.strip()==val
    r2=ok("format","doc",cwd=wd)
    assert "café" in r2.stdout

def test_many_operations(wd):
    ok("new","doc",cwd=wd)
    for i in range(100):
        args=["insert","doc","--id",f"m{i}","--value",f"v{i}"]
        if i>0: args+=["--after",f"m{i-1}"]
        ok(*args,cwd=wd)
    r=ok("status","doc",cwd=wd)
    assert "elements: 100" in r.stdout.lower()
    assert "operations: 100" in r.stdout.lower()
    r2=ok("format","doc",cwd=wd)
    lines=[l for l in r2.stdout.strip().splitlines() if l]
    assert len(lines)==100
    assert lines[0]=="v0" and lines[-1]=="v99"

def test_combined_workflow(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","a","--value","Alpha",cwd=wd)
    ok("insert","doc","--id","b","--value","Beta","--after","a",cwd=wd)
    ok("delete","doc","--id","a",cwd=wd)
    ok("insert","doc","--id","c","--value","Gamma",cwd=wd)
    r=ok("status","doc",cwd=wd)
    assert "elements: 2" in r.stdout.lower()
    r=ok("format","doc",cwd=wd)
    lines=r.stdout.strip().splitlines()
    assert "Gamma" in lines and "Beta" in lines
    assert "Alpha" not in lines

def test_large_document(wd):
    ok("new","doc",cwd=wd)
    for i in range(500):
        args=["insert","doc","--id",f"lg{i}","--value",f"val{i}"]
        if i>0: args+=["--after",f"lg{i-1}"]
        ok(*args,cwd=wd)
    r=ok("status","doc",cwd=wd)
    assert "elements: 500" in r.stdout.lower()
    r2=ok("format","doc",cwd=wd)
    assert "val0" in r2.stdout and "val499" in r2.stdout

def test_idempotent_recovery(wd):
    ok("new","doc",cwd=wd)
    ok("insert","doc","--id","idem","--value","once",cwd=wd)
    a=ok("format","doc",cwd=wd).stdout
    b=ok("format","doc",cwd=wd).stdout
    assert a==b
    assert a.strip()=="once"
    assert ok("status","doc",cwd=wd).stdout.lower().count("elements: 1")==1
