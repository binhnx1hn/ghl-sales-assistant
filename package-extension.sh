#!/usr/bin/env bash
# ============================================================================
# GHL Sales Assistant — Chrome Extension Packaging Script (Linux/macOS)
# Creates a distributable .zip from extension/ folder
# Usage: ./package-extension.sh
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="$SCRIPT_DIR/extension"
DIST_DIR="$SCRIPT_DIR/dist"
FOLDER_NAME="ghl-sales-assistant-extension"

# --------------------------------------------------------------------------
# 1. Read version from manifest.json
# --------------------------------------------------------------------------
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    # Fallback: grep version from manifest
    VERSION=$(grep -oP '"version"\s*:\s*"\K[^"]+' "$EXT_DIR/manifest.json" || echo "1.0.0")
else
    PY=$(command -v python3 || command -v python)
    VERSION=$($PY -c "import json; print(json.load(open('$EXT_DIR/manifest.json'))['version'])" 2>/dev/null || echo "1.0.0")
fi

ZIP_NAME="${FOLDER_NAME}-v${VERSION}.zip"

echo "============================================"
echo "  GHL Sales Assistant — Extension Packager"
echo "  Version: $VERSION"
echo "============================================"
echo ""

# --------------------------------------------------------------------------
# 2. Clean dist/ folder
# --------------------------------------------------------------------------
if [ -d "$DIST_DIR" ]; then
    echo "🧹 Cleaning existing dist/ folder..."
    rm -rf "$DIST_DIR"
fi
mkdir -p "$DIST_DIR/$FOLDER_NAME"

# --------------------------------------------------------------------------
# 3. Copy extension files (excluding unwanted files)
# --------------------------------------------------------------------------
echo "📦 Copying extension files..."

# Use rsync if available, otherwise fall back to find+cp
if command -v rsync &>/dev/null; then
    rsync -a \
        --exclude='.git' \
        --exclude='*.md' \
        --exclude='.DS_Store' \
        --exclude='Thumbs.db' \
        --exclude='node_modules' \
        --exclude='*.svg' \
        "$EXT_DIR/" "$DIST_DIR/$FOLDER_NAME/"
else
    # Fallback: find + cp
    cd "$EXT_DIR"
    find . -type f \
        ! -path '*/.git/*' \
        ! -name '*.md' \
        ! -name '.DS_Store' \
        ! -name 'Thumbs.db' \
        ! -path '*/node_modules/*' \
        ! -name '*.svg' \
        | while IFS= read -r file; do
            dest_dir="$DIST_DIR/$FOLDER_NAME/$(dirname "$file")"
            mkdir -p "$dest_dir"
            cp "$file" "$dest_dir/"
        done
    cd "$SCRIPT_DIR"
fi

# --------------------------------------------------------------------------
# 4. Create .zip archive
# --------------------------------------------------------------------------
echo "🗜️  Creating $ZIP_NAME..."

cd "$DIST_DIR"
if command -v zip &>/dev/null; then
    zip -r "$ZIP_NAME" "$FOLDER_NAME/" -q
else
    # Fallback: tar + gzip note
    echo "⚠️  'zip' command not found. Attempting with python..."
    PY=$(command -v python3 || command -v python)
    $PY -c "
import zipfile, os
with zipfile.ZipFile('$ZIP_NAME', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('$FOLDER_NAME'):
        for f in files:
            filepath = os.path.join(root, f)
            zf.write(filepath)
"
fi
cd "$SCRIPT_DIR"

# --------------------------------------------------------------------------
# 5. Show summary
# --------------------------------------------------------------------------
ZIP_PATH="$DIST_DIR/$ZIP_NAME"
FILE_SIZE=$(du -h "$ZIP_PATH" | cut -f1)
FILE_COUNT=$(find "$DIST_DIR/$FOLDER_NAME" -type f | wc -l | tr -d ' ')

echo ""
echo "✅ Package created successfully!"
echo "============================================"
echo "  Output:  dist/$ZIP_NAME"
echo "  Size:    $FILE_SIZE"
echo "  Files:   $FILE_COUNT"
echo "============================================"
echo ""
echo "📋 Contents:"
find "$DIST_DIR/$FOLDER_NAME" -type f | sed "s|$DIST_DIR/$FOLDER_NAME/|  |" | sort
echo ""
echo "============================================"
echo "  📌 How to install in Chrome:"
echo "  1. Unzip dist/$ZIP_NAME"
echo "  2. Open chrome://extensions"
echo "  3. Enable 'Developer mode' (top right)"
echo "  4. Click 'Load unpacked'"
echo "  5. Select the unzipped $FOLDER_NAME folder"
echo "============================================"
