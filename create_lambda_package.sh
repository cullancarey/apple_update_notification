#!/usr/bin/env bash
# create_lambda_package.sh
# Build self-contained Lambda deployment packages for each handler

set -euo pipefail

echo "Executing create_lambda_package.sh..."

# Work from the repo root regardless of where this is invoked
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

# Define Lambda handlers to package
LAMBDA_HANDLERS=("apple_web_scrape")

# --- Pick a Python interpreter compatible with pyproject requires-python (>=3.13) ---
is_compatible_python() {
  local candidate="$1"
  "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)' >/dev/null 2>&1
}

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but not installed. Install it from https://docs.astral.sh/uv/ and retry."
  exit 127
fi
uv --version || true

if [[ -n "${PYTHON_BIN:-}" ]]; then
  if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Configured PYTHON_BIN ('$PYTHON_BIN') was not found on PATH."
    exit 127
  fi
  if ! is_compatible_python "$PYTHON_BIN"; then
    echo "Configured PYTHON_BIN ('$PYTHON_BIN') must be Python >= 3.13 to match pyproject.toml requires-python."
    exit 1
  fi
else
  for candidate in python3.13 python3.14 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && is_compatible_python "$candidate"; then
      PYTHON_BIN="$candidate"
      break
    fi
  done

  # Fall back to uv-managed interpreter discovery (works well in CI images with uv preinstalled).
  if [[ -z "${PYTHON_BIN:-}" ]]; then
    UV_PYTHON_PATH="$(uv python find 3.13 2>/dev/null || true)"
    if [[ -n "$UV_PYTHON_PATH" && -x "$UV_PYTHON_PATH" ]] && is_compatible_python "$UV_PYTHON_PATH"; then
      PYTHON_BIN="$UV_PYTHON_PATH"
    fi
  fi

  if [[ -z "${PYTHON_BIN:-}" ]]; then
    echo "No compatible Python interpreter found. Expected Python >= 3.13 (tried python3.13/python3.14/python3/python and uv python find 3.13)."
    exit 1
  fi
fi

echo "Using Python interpreter: $PYTHON_BIN"
"$PYTHON_BIN" --version || true

# Always start clean
echo "Removing any previous artifacts"
rm -f *.zip
rm -rf package_*

LAMBDA_REQ_FILE=".tmp_lambda_requirements.txt"
echo "Exporting runtime dependency lock from pyproject.toml"
uv export --no-dev --no-hashes --format requirements-txt > "$LAMBDA_REQ_FILE"

# Build each Lambda package
for HANDLER in "${LAMBDA_HANDLERS[@]}"; do
  echo ""
  echo "========================================="
  echo "Building package for: $HANDLER"
  echo "========================================="
  
  PKG_DIR="package_${HANDLER}"
  ZIP_NAME="${HANDLER}.zip"
  
  echo "Making package directory: $PKG_DIR"
  mkdir -p "$PKG_DIR" 
  
  echo "Copying Lambda handler and shared utilities"
  cp "lambdas/${HANDLER}.py" "$PKG_DIR/"
  cp "lambdas/apple_utils.py" "$PKG_DIR/"
  
  echo "Installing dependencies to $PKG_DIR"
  uv pip install --python "$PYTHON_BIN" --target "$PKG_DIR" -r "$LAMBDA_REQ_FILE"
  
  echo "Removing __pycache__ and *.pyc to reduce package size"
  find "$PKG_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} + || true
  find "$PKG_DIR" -type f -name "*.pyc" -delete || true
  
  echo "Creating deployment package: $ZIP_NAME"
  (
    cd "$PKG_DIR"
    zip -r -q -X "../$ZIP_NAME" .
  )
  
  echo "✓ Package created: $PWD/$ZIP_NAME"
  
  echo "Cleaning up temporary directory: $PKG_DIR"
  rm -rf "$PKG_DIR"
done

rm -f "$LAMBDA_REQ_FILE"

echo ""
echo "========================================="
echo "Build complete! Created packages:"
for HANDLER in "${LAMBDA_HANDLERS[@]}"; do
  echo "  - ${HANDLER}.zip"
done
echo "========================================="