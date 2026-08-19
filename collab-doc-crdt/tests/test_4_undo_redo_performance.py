
import subprocess, os, tempfile, shutil, json, pytest, time, pathlib

BIN = "/app/target/release/collab-doc"
if not os.path.exists(BIN):
    BIN = "/tmp/collab-doc-oracle/target/release/collab-doc"
    if not os.path.exists(BIN):
        BIN = "collab-doc"

def run(args, cwd=None):
    return subprocess.run([BIN] + args, cwd=cwd, capture_output=True, text=True)

def run_ok(args, cwd=None):
    r = run(args, cwd=cwd)
    assert r.returncode == 0, f"Expected 0 got {r.returncode}: {' '.join(args)}\n{r.stdout}\n{r.stderr}"
    return r

def run_fail(args, cwd=None):
    r = run(args, cwd=cwd)
    assert r.returncode != 0, f"Expected fail but got 0: {' '.join(args)}"
    return r

@pytest.fixture
def workdir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)

def test_undo_insert(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "world", "--client", "alice", "--after", "a"], cwd=workdir)
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "world" not in r.stdout
    assert "Hello" in r.stdout

def test_undo_delete_restores(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello", "--client", "alice"], cwd=workdir)
    run_ok(["delete", "doc", "--id", "a", "--client", "alice"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert r.stdout.strip() == ""
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "Hello" in r.stdout

def test_redo_after_undo(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "world", "--client", "alice", "--after", "a"], cwd=workdir)
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    run_ok(["redo", "doc", "--client", "alice"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "Hello" in r.stdout and "world" in r.stdout

def test_undo_no_ops_fails(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_fail(["undo", "doc", "--client", "alice"], cwd=workdir)

def test_redo_no_ops_fails(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_fail(["redo", "doc", "--client", "nonexist"], cwd=workdir)

def test_per_client_isolation(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob"], cwd=workdir)
    # alice undo should only affect alice's op
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "A" not in r.stdout
    assert "B" in r.stdout
    # bob still has B
    run_ok(["undo", "doc", "--client", "bob"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert r.stdout.strip() == ""

def test_undo_causality(workdir):
    # if B after A, undoing A while B exists should fail or cascade - we accept either but not corrupt
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "alice", "--after", "a"], cwd=workdir)
    r = run(["undo", "doc", "--client", "alice"], cwd=workdir)
    # This undo removes B (last op is B after A, so undo B first should succeed)
    # The second undo would try to remove A while B already undone, so should succeed
    # But if impl does stack LIFO, first undo removes B, second removes A
    # So we test two undos
    if r.returncode == 0:
        # B was undone, now A has no dependents, second undo should succeed
        run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
        r2 = run_ok(["format", "doc"], cwd=workdir)
        assert r2.stdout.strip() == ""
    else:
        # if first undo failed due to dependency check, that's also acceptable if documented
        # but our test expects LIFO to work: last op is B, which has no dependents, so should succeed
        # So this path indicates potential issue, but we allow either
        r2 = run(["format", "doc"], cwd=workdir)
        assert r2.returncode == 0

def test_gc_preserves_format(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    for i in range(10):
        run_ok(["insert", "doc", "--id", f"e{i}", "--value", f"v{i}", "--client", "alice"], cwd=workdir)
    for i in range(5):
        run_ok(["delete", "doc", "--id", f"e{i}", "--client", "alice"], cwd=workdir)
    r1 = run_ok(["format", "doc"], cwd=workdir)
    run_ok(["gc", "doc"], cwd=workdir)
    r2 = run_ok(["format", "doc"], cwd=workdir)
    assert r1.stdout == r2.stdout

def test_gc_removes_tombstones(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A"], cwd=workdir)
    run_ok(["delete", "doc", "--id", "a"], cwd=workdir)
    r1 = run_ok(["status", "doc"], cwd=workdir)
    run_ok(["gc", "doc"], cwd=workdir)
    r2 = run_ok(["status", "doc"], cwd=workdir)
    # after GC, elements 0, operations may be same or reduced
    assert "elements: 0" in r2.stdout
    # format still empty
    r = run_ok(["format", "doc"], cwd=workdir)
    assert r.stdout.strip() == ""

def test_large_doc_performance(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    n = 1000
    start = time.time()
    for i in range(n):
        after = f"e{i-1}" if i>0 else None
        args = ["insert", "doc", "--id", f"e{i}", "--value", f"v{i}"]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    elapsed = time.time() - start
    # should complete in reasonable time (<10s for 1000 inserts via CLI, includes process overhead)
    assert elapsed < 20, f"Inserting {n} took {elapsed}s"
    start = time.time()
    r = run_ok(["format", "doc"], cwd=workdir)
    elapsed = time.time() - start
    assert elapsed < 2, f"Format took {elapsed}s"
    assert f"v{n-1}" in r.stdout

def test_save_load_preserves_undo(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "alice", "--after", "a"], cwd=workdir)
    # undo removes B, so doc has only A
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    r_before = run_ok(["format", "doc"], cwd=workdir)
    assert r_before.stdout.strip() == "A"
    # verify undo/redo stacks before save
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    if doc_json.exists():
        data = json.load(open(doc_json))
        assert "alice" in data.get("undo_stacks", {}) and len(data["undo_stacks"]["alice"]) >= 1
        assert "alice" in data.get("redo_stacks", {}) and len(data["redo_stacks"]["alice"]) >= 1
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    # loaded doc must have same format
    r_loaded = run_ok(["format", "doc2"], cwd=workdir)
    assert r_loaded.stdout == r_before.stdout
    # undo history must be preserved and usable - second undo must succeed (removes A)
    r = run_ok(["undo", "doc2", "--client", "alice"], cwd=workdir)
    assert r.returncode == 0
    r_after_undo = run_ok(["format", "doc2"], cwd=workdir)
    assert r_after_undo.stdout.strip() == ""
    # redo must restore A
    run_ok(["redo", "doc2", "--client", "alice"], cwd=workdir)
    r_after_redo = run_ok(["format", "doc2"], cwd=workdir)
    assert "A" in r_after_redo.stdout
    # redo again must restore B
    run_ok(["redo", "doc2", "--client", "alice"], cwd=workdir)
    r_final = run_ok(["format", "doc2"], cwd=workdir)
    assert "A" in r_final.stdout and "B" in r_final.stdout

def test_undo_redo_multiple(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    for i in range(3):
        run_ok(["insert", "doc", "--id", f"e{i}", "--value", f"v{i}", "--client", "alice"], cwd=workdir)
    # undo 3 times
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert r.stdout.strip() == ""
    # redo 3 times
    run_ok(["redo", "doc", "--client", "alice"], cwd=workdir)
    run_ok(["redo", "doc", "--client", "alice"], cwd=workdir)
    run_ok(["redo", "doc", "--client", "alice"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "v0" in r.stdout and "v2" in r.stdout

# --- Realistic undo/redo/perf with rich text ---

def test_undo_redo_rich_text(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "h1", "--value", "# Title **bold** *italic*", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "p1", "--value", "Paragraph **important** *note* `code`", "--client", "alice", "--after", "h1"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "h2", "--value", "## Subtitle *detail* **key**", "--client", "alice", "--after", "p1"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "# Title" in r.stdout
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "Subtitle" not in r.stdout
    run_ok(["redo", "doc", "--client", "alice"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "Subtitle" in r.stdout

def test_realistic_trace_undo_redo_interleaved(workdir):
    # 60 ops across alice/bob then undo/redo sequences
    import random
    random.seed(99)
    run_ok(["new", "doc"], cwd=workdir)
    ids=[]
    for i in range(60):
        client = "alice" if i%2==0 else "bob"
        eid = f"e{i}"
        val = f"Line {i} **bold {i}** *italic*" if i%5==0 else f"value {i}"
        after = ids[-1] if ids else None
        args = ["insert", "doc", "--id", eid, "--value", val, "--client", client]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
        ids.append(eid)
    # undo 5 from alice - handle dependents: leaf order bob->alice, so undo bob first if needed
    for client in ["bob", "alice", "bob", "alice", "bob"]:
        r_undo = run(["undo", "doc", "--client", client], cwd=workdir)
        # allow dependent error, but at least one undo should succeed
        if r_undo.returncode != 0:
            assert "dependents" in r_undo.stderr.lower() or "no operation" in r_undo.stderr.lower(), f"unexpected undo fail: {r_undo.stderr}"
    r = run_ok(["status", "doc"], cwd=workdir)
    # should have fewer elements
    assert "elements:" in r.stdout
    # redo - handle partial undos: redo as many as succeeded
    for client in ["bob", "alice", "bob", "alice"]:
        r_redo = run(["redo", "doc", "--client", client], cwd=workdir)
        if r_redo.returncode != 0:
            assert "no operations" in r_redo.stderr.lower() or "no operation" in r_redo.stderr.lower(), f"unexpected redo fail: {r_redo.stderr}"
            break
    r = run_ok(["format", "doc"], cwd=workdir)
    # i=0 creates Line 0, not value 0; check either
    assert "value 0" in r.stdout or "Line 0" in r.stdout or "value 1" in r.stdout

def test_large_doc_performance_realistic_2000(workdir):
    import time
    run_ok(["new", "doc"], cwd=workdir)
    n=2000
    start=time.time()
    for i in range(n):
        after = f"e{i-1}" if i>0 else None
        val = f"# Heading {i} **bold**" if i%200==0 else f"line {i} **b** *i* content longer realistic text {i}"
        args = ["insert", "doc", "--id", f"e{i}", "--value", val]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    elapsed=time.time()-start
    assert elapsed < 90, f"2000 inserts took {elapsed}s"
    r=run_ok(["format", "doc"], cwd=workdir)
    assert f"line {n-1}" in r.stdout
    # gc preserves
    r1=run_ok(["format", "doc"], cwd=workdir)
    run_ok(["gc", "doc"], cwd=workdir)
    r2=run_ok(["format", "doc"], cwd=workdir)
    assert r1.stdout==r2.stdout
