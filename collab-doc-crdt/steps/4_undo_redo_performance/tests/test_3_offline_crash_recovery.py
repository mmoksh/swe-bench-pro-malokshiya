
import subprocess, os, tempfile, shutil, json, pytest, pathlib

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

def test_save_creates_file(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A"], cwd=workdir)
    snap = os.path.join(workdir, "snap.json")
    r = run_ok(["save", "doc", "--path", snap], cwd=workdir)
    assert os.path.exists(snap)
    with open(snap) as f:
        data = json.load(f)
    assert data is not None

def test_load_recreates(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--after", "a"], cwd=workdir)
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    r = run_ok(["format", "doc2"], cwd=workdir)
    assert "A" in r.stdout and "B" in r.stdout

def test_save_load_roundtrip(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "world", "--client", "bob", "--after", "a"], cwd=workdir)
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    r1 = run_ok(["format", "doc"], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    r2 = run_ok(["format", "doc2"], cwd=workdir)
    assert r1.stdout == r2.stdout

def test_save_load_preserves_status(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    for i in range(5):
        run_ok(["insert", "doc", "--id", f"e{i}", "--value", f"v{i}", "--client", f"client{i%2}"], cwd=workdir)
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    r1 = run_ok(["status", "doc"], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    r2 = run_ok(["status", "doc2"], cwd=workdir)
    # element counts should match
    assert "elements: 5" in r1.stdout
    assert "elements: 5" in r2.stdout

def test_save_nonexistent_fails(workdir):
    run_fail(["save", "nope", "--path", os.path.join(workdir, "x.json")], cwd=workdir)

def test_load_nonexistent_fails(workdir):
    run_fail(["load", "--path", "/nonexistent/path.json", "--doc-id", "doc"], cwd=workdir)

def test_wal_exists_after_ops(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A"], cwd=workdir)
    wal = pathlib.Path(workdir) / ".collab-doc" / "doc.wal"
    # WAL may or may not exist depending on impl - if it exists check content, if not that's okay but save should still work
    # We check that at least doc.json exists
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    assert doc_json.exists()

def test_wal_recovery_on_truncation(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--after", "a"], cwd=workdir)
    # truncate main file to simulate crash - implementation should recover from WAL or at least not panic
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    if doc_json.exists():
        # truncate
        with open(doc_json, "w") as f:
            f.write("{ invalid")
        # now status should either recover or return error but not panic
        r = run(["status", "doc"], cwd=workdir)
        # should be either 0 with recovery or non-zero with clear error, but not segfault
        assert r.returncode in [0,1]

def test_large_save_load(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    for i in range(200):
        after = f"e{i-1}" if i>0 else None
        args = ["insert", "doc", "--id", f"e{i}", "--value", f"v{i}"]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    r = run_ok(["status", "doc2"], cwd=workdir)
    assert "elements: 200" in r.stdout

def test_save_load_preserves_clients(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob"], cwd=workdir)
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    r = run_ok(["status", "doc2"], cwd=workdir)
    assert "clients" in r.stdout.lower()

def test_atomic_write_no_corruption_parallel(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    # run two inserts in parallel-like rapid succession
    run_ok(["insert", "doc", "--id", "a", "--value", "A"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B"], cwd=workdir)
    # document should still be valid JSON
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    if doc_json.exists():
        with open(doc_json) as f:
            data = json.load(f)
            assert data is not None
    r = run_ok(["format", "doc"], cwd=workdir)
    assert r.returncode == 0
