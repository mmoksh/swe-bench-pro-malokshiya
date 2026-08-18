#!/bin/bash
set -e
export PATH="/app/target/release:/app/target/debug:/app:/root/.cargo/bin:/usr/local/cargo/bin:${PATH}"

# Ensure python3 exists
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found, attempting install..."
  apt-get update 2>&1 | tail -5 || true
  apt-get install -y python3 python3-pip 2>&1 | tail -5 || true
fi

# Ensure pytest available - install at runtime with proxy retries
if ! python3 -m pytest --version >/dev/null 2>&1; then
  echo "pytest not found, installing at runtime..."
  # Try with fwdproxy if available, else direct
  for i in 1 2 3; do
    python3 -m pip install --no-cache-dir pytest pytest-xdist 2>&1 | tail -5 && break
    echo "pip install attempt $i failed, retrying..."
    sleep 2
  done
  # Verify
  python3 -m pytest --version 2>&1 | head -1 || echo "pytest still not available, trying pip3"
  if ! python3 -m pytest --version >/dev/null 2>&1; then
    pip3 install --no-cache-dir pytest pytest-xdist 2>&1 | tail -5 || true
  fi
fi

echo "Tool versions: cargo=$(cargo --version 2>&1 | head -1), python3=$(python3 --version 2>&1), pytest=$(python3 -m pytest --version 2>&1 | head -1)"

NPROC=$(nproc 2>/dev/null || echo 1)
WORKERS=$((NPROC < 8 ? NPROC : 8))
# Cap workers to avoid 166 workers issue
if [ "$WORKERS" -gt 8 ]; then WORKERS=8; fi

run_all_tests() {
  echo "Running all tests..."
  cd /
  if [ "$WORKERS" -gt 1 ]; then
    python3 -m pytest tests -v -n "$WORKERS" --tb=short 2>&1 || \
      python3 -m pytest tests -v --tb=short 2>&1 || true
  else
    python3 -m pytest tests -v --tb=short 2>&1 || true
  fi
}

run_selected_tests() {
  local test_files=("$@")
  echo "Running selected tests: ${test_files[*]}"
  cd /

  local -A seen=()
  local test_file test_path
  for test_file in "${test_files[@]}"; do
    test_path="${test_file%%::*}"
    if [ -n "${seen[$test_path]:-}" ]; then
      continue
    fi
    seen[$test_path]=1
    echo "Running test file: $test_path"
    if [ "$WORKERS" -gt 1 ]; then
      python3 -m pytest "$test_path" -v -n "$WORKERS" --tb=short 2>&1 || \
        python3 -m pytest "$test_path" -v --tb=short 2>&1 || true
    else
      python3 -m pytest "$test_path" -v --tb=short 2>&1 || true
    fi
  done
}

if [ $# -eq 0 ]; then
  run_all_tests
  exit $?
fi

if [[ "$1" == *","* ]]; then
  IFS=',' read -r -a TEST_FILES <<< "$1"
else
  TEST_FILES=("$@")
fi

run_selected_tests "${TEST_FILES[@]}"
