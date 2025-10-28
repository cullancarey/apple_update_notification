#!/usr/bin/env bash
# create_lambda_package.sh
# Build a Lambda-compatible deployment zip at repo root: ./apple_utils.zip

set -euo pipefail

echo "Executing create_lambda_package.sh..."

# Work from the repo root regardless of where this is invoked
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

PKG_DIR="package"
ZIP_NAME="apple_utils.zip"

# --- NEW: pick a Python interpreter (python3 > python), allow override via $PYTHON_BIN ---
if [[ -z "${PYTHON_BIN:-}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "No python interpreter found (looked for python3, python). Install Python 3 and retry."
    exit 127
  fi
fi
echo "Using Python interpreter: $PYTHON_BIN"
$PYTHON_BIN --version || true
$PYTHON_BIN -m pip --version || true
# --- END NEW ---

# Always start clean
echo "Removing any previous artifacts"
rm -f "$ZIP_NAME"
rm -rf "$PKG_DIR"

echo "Making package directory"
mkdir -p "$PKG_DIR"

echo "Copying python script(s) to package directory"
# NOTE: apple_utils.py is your shared/util module; include it at the top level of the zip
cp lambdas/apple_utils.py "$PKG_DIR/"

echo "Installing requirements to package directory"
# Use the detected interpreter to ensure correct pip
$PYTHON_BIN -m pip install --upgrade --target "$PKG_DIR" -r ./requirements.txt

# Optional: strip __pycache__ and .pyc to reduce size
echo "Removing __pycache__ and *.pyc"
find "$PKG_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} + || true
find "$PKG_DIR" -type f -name "*.pyc" -delete || true

# Create the zip with stable metadata (-X) and quiet (-q), recurse (-r)
echo "Zipping contents into deployment package"
(
  cd "$PKG_DIR"
  # -X: exclude extra file attributes; helps reproducibility
  # -r: recurse; -q: quiet
  zip -r -q -X "../$ZIP_NAME" .
)

echo "Deployment package created at: $PWD/$ZIP_NAME"

# Cleanup working directory
echo "Removing package directory"
rm -rf "$PKG_DIR"

# Print the absolute path for CI logs
echo "Build complete: $(pwd)/$ZIP_NAME"