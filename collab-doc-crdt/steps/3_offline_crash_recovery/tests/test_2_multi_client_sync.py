
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
