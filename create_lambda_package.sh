#!/usr/bin/env bash
# create_lambda_package.sh
# Build self-contained Lambda deployment packages for each handler

set -euo pipefail

echo "Executing create_lambda_package.sh..."

# Work from the repo root regardless of where this is invoked
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

# Define Lambda handlers to package
LAMBDA_HANDLERS=("apple_web_scrape" "apple_send_update")

# --- Pick a Python interpreter (python3 > python), allow override via $PYTHON_BIN ---
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

# Always start clean
echo "Removing any previous artifacts"
rm -f *.zip
rm -rf package_*

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
  $PYTHON_BIN -m pip install --upgrade --target "$PKG_DIR" -r ./requirements.txt
  
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

echo ""
echo "========================================="
echo "Build complete! Created packages:"
for HANDLER in "${LAMBDA_HANDLERS[@]}"; do
  echo "  - ${HANDLER}.zip"
done
echo "========================================="