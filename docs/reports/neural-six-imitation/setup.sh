#!/usr/bin/env bash
# Run inside the disposable pod. Scientific execution is a separate explicit launch.
set -euo pipefail
export UV_CACHE_DIR=/workspace/uv-cache
export UV_PYTHON_INSTALL_DIR=/workspace/python
export CARGO_HOME=/workspace/cargo
export RUSTUP_HOME=/workspace/rustup
export PATH="$CARGO_HOME/bin:/root/.local/bin:$PATH"
if ! command -v cargo >/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
fi
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
uv python install 3.11
uv venv --python 3.11 /workspace/venv
uv pip install --python /workspace/venv/bin/python 'torch==2.5.1' --index-url https://download.pytorch.org/whl/cu124
uv pip install --python /workspace/venv/bin/python -r requirements-dev.txt
cargo build --release --locked --manifest-path native/hu20-trainer/Cargo.toml \
  --example nplayer_features --example nplayer_paired_arena --example nplayer_allin_equity \
  --example nplayer_network_parity
echo 'Setup complete; qualification and scientific work have not started.'
