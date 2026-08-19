
import subprocess, os, tempfile, shutil, pytest

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

def test_insert_with_client(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    r = run_ok(["get", "doc", "--id", "a"], cwd=workdir)
    assert "A" in r.stdout

def test_multi_client_format(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob", "--after", "a"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "A" in r.stdout and "B" in r.stdout

def test_sync_command(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    r = run_ok(["sync", "doc", "--from", "alice", "--to", "bob"], cwd=workdir)
    assert r.returncode == 0

def test_merge_command(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob", "--after", "a"], cwd=workdir)
    run_ok(["merge", "doc", "--clients", "alice,bob"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "A" in r.stdout and "B" in r.stdout

def test_merge_order_independence(workdir):
    # same ops, different merge client order should give same format
    def scenario(order):
        d = tempfile.mkdtemp()
        run_ok(["new", "doc"], cwd=d)
        run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=d)
        run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob", "--after", "a"], cwd=d)
        run_ok(["insert", "doc", "--id", "c", "--value", "C", "--client", "carol", "--after", "a"], cwd=d)
        run_ok(["merge", "doc", "--clients", order], cwd=d)
        r = run_ok(["format", "doc"], cwd=d)
        shutil.rmtree(d)
        return r.stdout
    out1 = scenario("alice,bob,carol")
    out2 = scenario("carol,bob,alice")
    out3 = scenario("bob,alice,carol")
    assert out1 == out2 == out3

def test_status_clients(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob"], cwd=workdir)
    r = run_ok(["status", "doc"], cwd=workdir)
    assert "clients" in r.stdout.lower()

def test_log_command(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    r = run_ok(["log", "doc"], cwd=workdir)
    assert "alice" in r.stdout

def test_log_filter_client(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob"], cwd=workdir)
    r = run_ok(["log", "doc", "--client", "alice"], cwd=workdir)
    assert "alice" in r.stdout
    assert "bob" not in r.stdout

def test_concurrent_inserts_deterministic(workdir):
    # two clients insert after same element concurrently - should be deterministic
    def run_once():
        d = tempfile.mkdtemp()
        run_ok(["new", "doc"], cwd=d)
        run_ok(["insert", "doc", "--id", "base", "--value", "BASE"], cwd=d)
        run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice", "--after", "base"], cwd=d)
        run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob", "--after", "base"], cwd=d)
        run_ok(["merge", "doc", "--clients", "alice,bob"], cwd=d)
        r = run_ok(["format", "doc"], cwd=d)
        out = r.stdout
        shutil.rmtree(d)
        return out
    outs = [run_once() for _ in range(5)]
    # all should be identical (deterministic)
    assert all(x == outs[0] for x in outs)

def test_causal_ordering(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    run_ok(["sync", "doc", "--from", "alice", "--to", "bob"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "b", "--value", "B", "--client", "bob", "--after", "a"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    lines = r.stdout.strip().split("\n")
    # A should come before B since B after A
    assert lines.index("A") < lines.index("B")

def test_merge_three_clients(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    for client, val in [("alice","A"),("bob","B"),("carol","C")]:
        run_ok(["insert", "doc", "--id", client, "--value", val, "--client", client], cwd=workdir)
    run_ok(["merge", "doc", "--clients", "alice,bob,carol"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "A" in r.stdout and "B" in r.stdout and "C" in r.stdout

def test_client_clock_preserved_after_reload(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "A", "--client", "alice"], cwd=workdir)
    r = run_ok(["status", "doc"], cwd=workdir)
    assert "clients" in r.stdout.lower()
    # reload via new invocation
    r2 = run_ok(["status", "doc"], cwd=workdir)
    assert "clients" in r2.stdout.lower()

def test_backward_compat_no_client(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "a", "--value", "Hello"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "Hello" in r.stdout

# --- Realistic multi-client interleaved trace (50+ ops) ---
REALISTIC_TEXTS = [
    "# Sprint Doc **Q3** *Planning*",
    "## Goals *Increase* **velocity**",
    "### Attendees: **Alice** *Bob* Carol",
    "- **Task 1**: *Design* CRDT **core**",
    "- **Task 2**: *Implement* sync **protocol**",
    "Review: **LGTM** *needs* `cargo test`",
    "> Quote: *offline* **recovery** is key",
    "```rust\nfn apply(op: Op) {}\n```",
    "Table | **A** | *B* |\n|---|---|\n|1|2|",
    "Notes: **summary** *next steps* ## Done",
]
CLIENTS = ["alice","bob","carol","dave"]

def _build_interleaved_trace(n=72):
    """Deterministic 72-op trace interleaving 4 clients, realistic text."""
    import random
    random.seed(2024)
    base_id = "base"
    ops = [( "alice", base_id, REALISTIC_TEXTS[0], None )]
    # subsequent ops chain off random predecessor to create realistic branching
    ids = [base_id]
    for i in range(1, n):
        client = CLIENTS[i % len(CLIENTS)]
        eid = f"{client}_{i}"
        val = REALISTIC_TEXTS[i % len(REALISTIC_TEXTS)] + f" #{i}"
        # pick after from recent ids (last 5) or base to keep causally valid
        after = random.choice(ids[-5:]) if len(ids) >= 5 else ids[-1]
        ops.append((client, eid, val, after))
        ids.append(eid)
    # shuffle to simulate interleaved arrival (but keep base first)
    head = ops[:1]
    tail = ops[1:]
    random.shuffle(tail)
    return head + tail

def test_multi_client_interleaved_realistic_72_ops(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    trace = _build_interleaved_trace(72)
    # apply with retry for after-not-found (out-of-order)
    pending = trace[:]
    attempts = 0
    max_attempts = len(pending)*10
    applied = set()
    # base already
    while pending and attempts < max_attempts:
        client, eid, val, after = pending.pop(0)
        args = ["insert", "doc", "--id", eid, "--value", val, "--client", client]
        if after:
            args += ["--after", after]
        r = run(args, cwd=workdir)
        if r.returncode != 0 and "not found" in (r.stderr.lower()+r.stdout.lower()) and "after" in (r.stderr.lower()+r.stdout.lower()):
            pending.append((client, eid, val, after))
        else:
            assert r.returncode == 0, f"insert {eid} failed: {r.stderr}"
            applied.add(eid)
        attempts += 1
    assert not pending, f"unresolved: {pending[:3]}"
    run_ok(["merge", "doc", "--clients", ",".join(CLIENTS)], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    # verify distinctive markers survive merge
    assert "Sprint Doc" in r.stdout
    assert "cargo test" in r.stdout
    r = run_ok(["status", "doc"], cwd=workdir)
    assert "elements: 72" in r.stdout
    # log should show all clients
    r = run_ok(["log", "doc"], cwd=workdir)
    for c in CLIENTS:
        assert c in r.stdout

def test_rich_text_multi_client(workdir):
    run_ok(["new", "doc"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "h1", "--value", "# Heading **bold** *italic*", "--client", "alice"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "p1", "--value", "Paragraph with **bold** and *italic* and `code`", "--client", "bob", "--after", "h1"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "h2", "--value", "## Subheading *notes* **important**", "--client", "carol", "--after", "p1"], cwd=workdir)
    run_ok(["insert", "doc", "--id", "q1", "--value", "> Blockquote **quote** *source*", "--client", "dave", "--after", "h2"], cwd=workdir)
    run_ok(["merge", "doc", "--clients", "alice,bob,carol,dave"], cwd=workdir)
    r = run_ok(["format", "doc"], cwd=workdir)
    assert "# Heading" in r.stdout
    assert "**bold**" in r.stdout
    assert "*italic*" in r.stdout

def test_merge_order_independence_large(workdir):
    # 60 ops, verify merge deterministic regardless of client order
    import tempfile, shutil
    def scenario(order):
        d = tempfile.mkdtemp()
        run_ok(["new", "doc"], cwd=d)
        trace = _build_interleaved_trace(60)
        pending = trace[:]
        attempts = 0
        max_attempts = len(pending)*10
        while pending and attempts < max_attempts:
            client, eid, val, after = pending.pop(0)
            args = ["insert", "doc", "--id", eid, "--value", val, "--client", client]
            if after:
                args += ["--after", after]
            r = run(args, cwd=d)
            if r.returncode != 0 and "not found" in (r.stderr.lower()+r.stdout.lower()):
                pending.append((client, eid, val, after))
            else:
                assert r.returncode == 0
            attempts += 1
        run_ok(["merge", "doc", "--clients", order], cwd=d)
        r = run_ok(["format", "doc"], cwd=d)
        out = r.stdout
        shutil.rmtree(d)
        return out
    out1 = scenario("alice,bob,carol,dave")
    out2 = scenario("dave,carol,bob,alice")
    out3 = scenario("bob,dave,alice,carol")
    assert out1 == out2 == out3

def test_large_sync_save_load_realistic(workdir):
    import os, json as _json
    run_ok(["new", "doc"], cwd=workdir)
    trace = _build_interleaved_trace(50)
    pending = trace[:]
    attempts = 0
    max_attempts = len(pending)*10
    while pending and attempts < max_attempts:
        client, eid, val, after = pending.pop(0)
        args = ["insert", "doc", "--id", eid, "--value", val, "--client", client]
        if after:
            args += ["--after", after]
        r = run(args, cwd=workdir)
        if r.returncode != 0 and "not found" in (r.stderr.lower()+r.stdout.lower()):
            pending.append((client, eid, val, after))
        else:
            assert r.returncode == 0
        attempts += 1
    snap = os.path.join(workdir, "snap.json")
    run_ok(["save", "doc", "--path", snap], cwd=workdir)
    run_ok(["load", "--path", snap, "--doc-id", "doc2"], cwd=workdir)
    r1 = run_ok(["format", "doc"], cwd=workdir)
    r2 = run_ok(["format", "doc2"], cwd=workdir)
    assert r1.stdout == r2.stdout
    r = run_ok(["status", "doc2"], cwd=workdir)
    assert "elements: 50" in r.stdout
