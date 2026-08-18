FROM python:3.11-bookworm

WORKDIR /app
RUN mkdir -p /logs /app

# Install pytest from vendored wheels
RUN mkdir -p /tmp/wheels
COPY *.whl /tmp/wheels/
RUN pip install --no-cache-dir /tmp/wheels/*.whl 2>&1 | tail -10 || pip install --no-cache-dir "pytest<8" pytest-xdist 2>&1 | tail -10 || true
RUN rm -rf /tmp/wheels

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain 1.79 --profile minimal 2>&1 | tail -10; echo "rustup done"
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo --version; python3 --version; pytest --version 2>&1 || python3 -m pytest --version 2>&1 || true

# Pre-cache cargo deps
RUN mkdir -p /tmp/cache_test && cd /tmp/cache_test && \
    printf '[package]\nname = "cache_test"\nversion = "0.1.0"\nedition = "2021"\n[dependencies]\nclap = { version = "=4.4.18", features = ["derive"] }\nserde = { version = "=1.0.219", features = ["derive"] }\nserde_json = "=1.0.143"\nuuid = { version = "=1.11.0", features = ["v4"] }\n' > Cargo.toml && \
    mkdir -p src && echo 'fn main(){}' > src/main.rs && cargo fetch 2>&1 | tail -10; rm -rf /tmp/cache_test || true
