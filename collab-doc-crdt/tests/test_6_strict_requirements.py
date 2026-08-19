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

# ── WAL replay strict ──────────────────────────────────────────────
def test_wal_replay_after_doc_deletion_restores(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Alpha", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "Beta", "--client", "bob", "--after", "a"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "c", "--value", "Gamma", "--client", "alice", "--after", "b"], cwd=workdir)
    r_before = run_ok(["format", "doc"], cwd=workdir)
    lines_before = r_before.stdout.strip().split("\n")
    assert lines_before == ["Alpha", "Beta", "Gamma"]
    s_before = run_ok(["status", "doc"], cwd=workdir)
    assert "elements: 3" in s_before.stdout.lower()
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    # delete main file - WAL must fully recover on next access
    if doc_json.exists():
        os.remove(doc_json)
    r_fmt = run_ok(["format", "doc"], cwd=workdir)
    assert r_fmt.stdout == r_before.stdout
    r_status = run_ok(["status", "doc"], cwd=workdir)
    assert "elements: 3" in r_status.stdout.lower()
    # second access idempotent
    r_fmt2 = run_ok(["format", "doc"], cwd=workdir)
    assert r_fmt2.stdout == r_before.stdout

def test_wal_replay_skips_corrupted_line_and_warns(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob", "--after", "a"], cwd=workdir)
    wal_path = pathlib.Path(workdir) / ".collab-doc" / "doc.wal"
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    r_before = run_ok(["format", "doc"], cwd=workdir)
    if wal_path.exists():
        with open(wal_path, "a") as f:
            f.write("INVALID JSON LINE\n")
            f.write('{"op_id":"partial"')  # truncated without newline
        if doc_json.exists():
            os.remove(doc_json)
        r = run_ok(["status", "doc"], cwd=workdir)
        assert r.returncode == 0
        assert "elements: 2" in r.stdout.lower()
        # corrupted lines must be reported on stderr
        assert "skipped" in r.stderr.lower() or "corrupt" in r.stderr.lower() or "warning" in r.stderr.lower()
        r_fmt = run_ok(["format", "doc"], cwd=workdir)
        assert r_fmt.stdout == r_before.stdout

def test_wal_replay_idempotent_double(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob", "--after", "a"], cwd=workdir)
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    wal_path = pathlib.Path(workdir) / ".collab-doc" / "doc.wal"
    # force WAL replay twice
    if doc_json.exists():
        os.remove(doc_json)
    run_ok(["status", "doc"], cwd=workdir)
    doc_after_first = json.load(open(doc_json))
    first_ops = len(doc_after_first["operations"])
    # second replay (remove again, replay from same WAL)
    # WAL may have been cleared after first replay - check behavior: second replay from fresh WAL still idempotent
    # Instead trigger replay by corrupting json again
    with open(doc_json, "w") as f:
        f.write("{ invalid")
    run_ok(["status", "doc"], cwd=workdir)
    doc_after_second = json.load(open(doc_json))
    assert doc_after_second["order"] == doc_after_first["order"]
    assert doc_after_second["elements"] == doc_after_first["elements"]
    assert len(doc_after_second["operations"]) == first_ops

def test_wal_ordering_preserved(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    for i in range(10):
        after = f"e{i-1}" if i > 0 else None
        args = ["insert", "doc", "--id", f"e{i}", "--value", f"v{i}", "--client", "alice"]
        if after:
            args += ["--after", after]
        run_ok(args, cwd=workdir)
    r_before = run_ok(["format", "doc"], cwd=workdir)
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    if doc_json.exists():
        os.remove(doc_json)
    r_after = run_ok(["format", "doc"], cwd=workdir)
    assert r_after.stdout == r_before.stdout
    assert r_after.stdout.strip().split("\n") == [f"v{i}" for i in range(10)]

# ── Save/load undo history strict ─────────────────────────────────
def test_save_load_undo_history_strict(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "alice", "--after", "a"], cwd=workdir)
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    r_before = run_ok(["format", "doc"], cwd=workdir)
    assert r_before.stdout.strip() == "A"
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    # snapshot must contain undo/redo history
    snap_data = json.load(open(snap))
    assert "undo_stacks" in snap_data
    assert "redo_stacks" in snap_data
    assert len(snap_data["undo_stacks"].get("alice", [])) >= 1
    assert len(snap_data["redo_stacks"].get("alice", [])) >= 1
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    r_loaded = run_ok(["format", "doc2"], cwd=workdir)
    assert r_loaded.stdout == r_before.stdout
    # strict: undo must succeed (not in [0,1])
    r = run_ok(["undo", "doc2", "--client", "alice"], cwd=workdir)
    assert r.returncode == 0
    assert run_ok(["format", "doc2"], cwd=workdir).stdout.strip() == ""
    run_ok(["redo", "doc2", "--client", "alice"], cwd=workdir)
    assert "A" in run_ok(["format", "doc2"], cwd=workdir).stdout
    run_ok(["redo", "doc2", "--client", "alice"], cwd=workdir)
    assert "A" in run_ok(["format", "doc2"], cwd=workdir).stdout and "B" in run_ok(["format", "doc2"], cwd=workdir).stdout

def test_save_load_redo_only_strict(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["undo", "doc", "--client", "alice"], cwd=workdir)
    assert run_ok(["format", "doc"], cwd=workdir).stdout.strip() == ""
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    # redo must succeed on loaded doc
    run_ok(["redo", "doc2", "--client", "alice"], cwd=workdir)
    assert "A" in run_ok(["format", "doc2"], cwd=workdir).stdout
    # further redo must fail (no more ops)
    run_fail(["redo", "doc2", "--client", "alice"], cwd=workdir)

# ── Vector-clock causality ────────────────────────────────────────
def test_vector_clock_monotonic(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    for i in range(5):
        args = ["insert", "doc", "--id", f"e{i}", "--value", f"v{i}", "--client", "alice"]
        if i > 0:
            args += ["--after", f"e{i-1}"]
        run_ok(args, cwd=workdir)
    data = json.load(open(pathlib.Path(workdir) / ".collab-doc" / "doc.json"))
    assert data["vector_clocks"]["alice"] == 5
    lamports = [op["lamport"] for op in data["operations"] if op["client_id"] == "alice"]
    assert lamports == [1, 2, 3, 4, 5]
    assert lamports == sorted(lamports)
    # each later lamport strictly greater than previous for same client
    for i in range(1, len(lamports)):
        assert lamports[i] > lamports[i - 1]

def test_vector_clock_multi_client_causal(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob", "--after", "a"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "c", "--value", "C", "--client", "alice", "--after", "b"], cwd=workdir)
    data = json.load(open(pathlib.Path(workdir) / ".collab-doc" / "doc.json"))
    assert data["vector_clocks"]["alice"] == 2
    assert data["vector_clocks"]["bob"] == 1
    # operations carry correct lamports
    alice_ops = [o for o in data["operations"] if o["client_id"] == "alice"]
    bob_ops = [o for o in data["operations"] if o["client_id"] == "bob"]
    assert alice_ops[0]["lamport"] == 1 and alice_ops[1]["lamport"] == 2
    assert bob_ops[0]["lamport"] == 1
    r = run_ok(["format", "doc"], cwd=workdir)
    lines = r.stdout.strip().split("\n")
    assert lines.index("A") < lines.index("B") < lines.index("C")
    # sync should not break causality - sync increments receiver clock
    run_ok(["sync", "doc", "--from", "alice", "--to", "bob"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "d", "--value", "D", "--client", "bob", "--after", "c"], cwd=workdir)
    data2 = json.load(open(pathlib.Path(workdir) / ".collab-doc" / "doc.json"))
    assert data2["vector_clocks"]["bob"] == 3
    r2 = run_ok(["format", "doc"], cwd=workdir)
    assert r2.stdout.strip().split("\n").index("C") < r2.stdout.strip().split("\n").index("D")

def test_vector_clock_preserved_across_save_load(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob", "--after", "a"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "c", "--value", "C", "--client", "alice", "--after", "b"], cwd=workdir)
    before = json.load(open(pathlib.Path(workdir) / ".collab-doc" / "doc.json"))["vector_clocks"]
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    after = json.load(open(pathlib.Path(workdir) / ".collab-doc" / "doc2.json"))["vector_clocks"]
    assert after == before

# ── Operation-ID collision rejection ───────────────────────────────
def test_operation_id_collision_rejected_via_wal(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    data = json.load(open(pathlib.Path(workdir) / ".collab-doc" / "doc.json"))
    op_id = data["operations"][0]["op_id"]
    wal_path = pathlib.Path(workdir) / ".collab-doc" / "doc.wal"
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    # inject duplicate op_id with different payload via WAL
    dup = {"op_id": op_id, "client_id": "evil", "lamport": 99, "timestamp": 123456, "kind": {"Insert": {"element_id": "evil", "value": "EVIL", "after": None}}}
    with open(wal_path, "a") as f:
        f.write(json.dumps(dup) + "\n")
    # force replay
    if doc_json.exists():
        os.remove(doc_json)
    r = run_ok(["status", "doc"], cwd=workdir)
    assert "elements: 1" in r.stdout.lower()
    assert r.returncode == 0
    r_fmt = run_ok(["format", "doc"], cwd=workdir)
    assert "EVIL" not in r_fmt.stdout
    assert "A" in r_fmt.stdout
    data2 = json.load(open(doc_json))
    assert len(data2["operations"]) == 1
    assert data2["operations"][0]["op_id"] == op_id

def test_element_id_collision_rejected_strict(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_fail(["insert", "doc", "--id", "a", "--value", "B", "--client", "bob"], cwd=workdir)
    run_fail(["insert", "doc", "--id", "a", "--value", "C"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert r.stdout.strip() == "A"
    data = json.load(open(pathlib.Path(workdir) / ".collab-doc" / "doc.json"))
    assert len(data["operations"]) == 1
    assert len(data["elements"]) == 1

# ── Byzantine corruption detection ────────────────────────────────
def test_byzantine_wal_corruption_warning(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    r_before = run_ok(["format", "doc"], cwd=workdir)
    wal_path = pathlib.Path(workdir) / ".collab-doc" / "doc.wal"
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    if wal_path.exists():
        with open(wal_path, "a") as f:
            f.write("BYZANTINE INVALID LINE\n")
            f.write("{ not valid json at all\n")
        if doc_json.exists():
            os.remove(doc_json)
        r = run_ok(["status", "doc"], cwd=workdir)
        assert r.returncode == 0
        assert "BYZANTINE" not in run_ok(["format", "doc"], cwd=workdir).stdout
        assert r_before.stdout == run_ok(["format", "doc"], cwd=workdir).stdout
        assert "skipped" in r.stderr.lower() or "corrupt" in r.stderr.lower() or "warning" in r.stderr.lower()

def test_byzantine_corrupted_snapshot_rejected(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    snap = os.path.join(workdir, "evil.json")
    # truncated invalid JSON
    with open(snap, "w") as f:
        f.write("{ invalid json")
    run_fail(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    # duplicate order injection via snapshot
    run_ok(["new", "doc2"], cwd=workdir)
    run_ok(["insert", "doc2", "--id", "x", "--value", "X", "--client", "alice"], cwd=workdir)
    evil_snap = os.path.join(workdir, "evil2.json")
    # create a snapshot with duplicate op content but valid JSON - should be loadable but verify handles it
    data = json.load(open(pathlib.Path(workdir) / ".collab-doc" / "doc2.json"))
    with open(evil_snap, "w") as f:
        json.dump(data, f)
    # loading valid snapshot must succeed
    run_ok(["load", "--path", evil_snap, "--doc-id", "doc3"], cwd=workdir)
    assert "X" in run_ok(["format", "doc3"], cwd=workdir).stdout
    # original doc still healthy
    assert "A" in run_ok(["format", "doc"], cwd=workdir).stdout

def test_byzantine_truncated_doc_recovery(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "World", "--client", "bob", "--after", "a"], cwd=workdir)
    r_before = run_ok(["format", "doc"], cwd=workdir)
    doc_json = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    # simulate torn write: truncate to partial JSON
    with open(doc_json, "w") as f:
        f.write('{"name": "doc", "order": [')
    r = run_ok(["format", "doc"], cwd=workdir)
    assert r.stdout == r_before.stdout
    # no panic, recovered correctly
    assert "Hello" in r.stdout and "World" in r.stdout

def test_byzantine_duplicate_order_handled(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob", "--after", "a"], cwd=workdir)
    doc_path = pathlib.Path(workdir) / ".collab-doc" / "doc.json"
    data = json.load(open(doc_path))
    data["order"] = ["a", "a", "b"]
    with open(doc_path, "w") as f:
        json.dump(data, f)
    # must not panic - either verify detects or format dedups gracefully
    r = run_ok(["format", "doc"], cwd=workdir)
    assert r.returncode == 0
    # dedup: A should appear exactly once
    assert r.stdout.count("A") == 1
    assert "B" in r.stdout
