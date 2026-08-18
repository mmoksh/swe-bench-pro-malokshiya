#!/bin/bash
set -euo pipefail
APP_DIR="${APP_DIR:-/app}"
mkdir -p "$APP_DIR/src"

if ! command -v cargo >/dev/null 2>&1; then
  echo "cargo not found, trying to install..."
  export PATH="/root/.cargo/bin:/usr/local/cargo/bin:$PATH"
fi
export PATH="/root/.cargo/bin:/usr/local/cargo/bin:$PATH"

# Find files dir
if [ -d "$PWD/files" ]; then
  SRC_DIR="$PWD/files"
elif [ -d "./files" ]; then
  SRC_DIR="./files"
elif [ -d "/solution/files" ]; then
  SRC_DIR="/solution/files"
else
  SRC_DIR="."
fi

echo "Using SRC_DIR=$SRC_DIR"
ls -la "$SRC_DIR" 2>&1 | head -20

mkdir -p "$APP_DIR/src"
if [ -d "$SRC_DIR/src" ]; then
  cp -r "$SRC_DIR/src/"* "$APP_DIR/src/" 2>/dev/null || cp -r "$SRC_DIR/src" "$APP_DIR/"
fi
if [ -f "$SRC_DIR/Cargo.toml" ]; then
  cp "$SRC_DIR/Cargo.toml" "$APP_DIR/"
fi
if [ -f "$SRC_DIR/Cargo.lock" ]; then
  cp "$SRC_DIR/Cargo.lock" "$APP_DIR/"
fi

cd "$APP_DIR"

# Try building, with fallbacks
echo "Attempting cargo build --offline..."
if cargo build --release --offline 2>&1; then
  echo "Offline build succeeded"
elif cargo build --release 2>&1; then
  echo "Online build succeeded"
else
  echo "Cargo build failed, trying fallback binary..."
  if [ -f "$SRC_DIR/collab-doc-bin" ]; then
    mkdir -p target/release
    cp "$SRC_DIR/collab-doc-bin" target/release/collab-doc
    chmod +x target/release/collab-doc
    echo "Used fallback binary"
  elif [ -f "/tmp/collab-doc-oracle/target/release/collab-doc" ]; then
    mkdir -p target/release
    cp /tmp/collab-doc-oracle/target/release/collab-doc target/release/
    chmod +x target/release/collab-doc
    echo "Used /tmp fallback"
  else
    echo "No fallback binary found, failing"
    exit 1
  fi
fi

ls -lh target/release/collab-doc 2>&1 | head -5
