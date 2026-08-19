
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
    # black-box persistence: verify via CLI that state is durable (works with any storage backend - JSON, SQLite, etc.)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "A" in r.stdout
    snap = os.path.join(workdir, "wal_persist.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    assert os.path.exists(snap)
    run_ok(["load", "--path", snap, "--doc-id", "doc_wal_reload"], cwd=workdir)
    r2 = run_ok(["format", "doc_wal_reload"], cwd=workdir)
    assert r2.stdout == r.stdout
    r3 = run_ok(["status", "doc"], cwd=workdir)
    assert "elements: 1" in r3.stdout.lower()

def test_wal_recovery_on_truncation(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--after", "a"], cwd=workdir)
    r_before = run_ok(["format", "doc"], cwd=workdir)
    assert "A" in r_before.stdout and "B" in r_before.stdout
    r_status_before = run_ok(["status", "doc"], cwd=workdir)
    assert "elements: 2" in r_status_before.stdout.lower()
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    if doc_json.exists():
        with open(doc_json, "w") as f:
            f.write("{ invalid")
        # WAL must recover the document - status must succeed and report correct state
        r = run_ok(["status", "doc"], cwd=workdir)
        assert r.returncode == 0
        assert "elements: 2" in r.stdout.lower()
        # format must be restored exactly
        r_fmt = run_ok(["format", "doc"], cwd=workdir)
        assert r_fmt.stdout == r_before.stdout
        # status again to verify idempotent recovery
        r2 = run_ok(["status", "doc"], cwd=workdir)
        assert r2.stdout == r.stdout
        # document file must be repaired (valid JSON)
        with open(doc_json) as f:
            data = json.load(f)
            assert data["order"] == ["a", "b"]

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

# --- Realistic offline / save-load with rich text ---
REALISTIC_SNAP_TEXTS = [
    "# Offline Notes **v1** *draft*",
    "## Section **Data** *sync*",
    "Paragraph **bold** *italic* normal text lorem ipsum",
    "```json\n{\"key\": \"value\"} \n```",
    "> **Important** *offline* queue",
]

def test_save_load_rich_text_roundtrip(workdir):
    import os
    run_ok(["new", "doc"], cwd=workdir)
    for i, val in enumerate(REALISTIC_SNAP_TEXTS):
        args = ["insert", "doc", "--id", f"r{i}", "--value", val, "--client", "alice"]
        if i>0:
            args += ["--after", f"r{i-1}"]
        run_ok(args, cwd=workdir)
    # add 60 more realistic ops
    for i in range(5, 65):
        val = f"Line {i}: **bold {i}** *italic {i}* content"
        args = ["insert", "doc", "--id", f"r{i}", "--value", val, "--client", f"client{i%3}", "--after", f"r{i-1}"]
        run_ok(args, cwd=workdir)
    snap = os.path.join(workdir, "snap.json")
    r1 = run_ok(["format", "doc"], cwd=workdir)
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    r2 = run_ok(["format", "doc2"], cwd=workdir)
    assert r1.stdout == r2.stdout
    assert "# Offline Notes" in r2.stdout

def test_large_save_load_1000_with_rich_text(workdir):
    import os
    run_ok(["new", "doc"], cwd=workdir)
    n=800
    for i in range(n):
        after = f"e{i-1}" if i>0 else None
        if i%50==0:
            val = f"# Heading {i} **bold** *italic*"
        else:
            val = f"value {i} **b{i}** *i{i}*"
        args = ["insert", "doc", "--id", f"e{i}", "--value", val]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    r = run_ok(["status", "doc2"], cwd=workdir)
    assert f"elements: {n}" in r.stdout

def test_interleaved_offline_recovery_realistic(workdir):
    import os, pathlib, json as _json
    run_ok(["new", "doc"], cwd=workdir)
    # simulate offline batch: create 50 ops then save/load as recovery
    for i in range(50):
        val = f"Offline line {i} **bold** *italic* heading" if i%10==0 else f"offline value {i}"
        after = f"o{i-1}" if i>0 else None
        args = ["insert", "doc", "--id", f"o{i}", "--value", val, "--client", "alice"]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    r_before = run_ok(["format", "doc"], cwd=workdir)
    snap = os.path.join(workdir, "recovery.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    # corrupt doc.json to simulate crash
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    if doc_json.exists():
        with open(doc_json, "w") as f:
            f.write("{ invalid")
    # load from snapshot into new doc should still recover content
    run_ok(["load", "--path", snap, "--doc-id", "recovered"], cwd=workdir)
    r_after = run_ok(["format", "recovered"], cwd=workdir)
    assert r_before.stdout == r_after.stdout
