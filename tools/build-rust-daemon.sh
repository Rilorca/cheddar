#!/bin/sh
set -e

MANIFEST_DIR="$1"
OUTPUT="$2"

if [ -f "$MANIFEST_DIR/Cargo.toml" ]; then
    MANIFEST_FILE="$MANIFEST_DIR/Cargo.toml"
else
    MANIFEST_FILE="$MANIFEST_DIR"
fi

echo "Building Cheddar Rust AutoPilot daemon ($MANIFEST_FILE)..."
cargo build --manifest-path "$MANIFEST_FILE" --release

TARGET_DIR="$(dirname "$MANIFEST_FILE")/target/release"
cp -f "$TARGET_DIR/cheddar-autopilot" "$OUTPUT"
chmod +x "$OUTPUT"
