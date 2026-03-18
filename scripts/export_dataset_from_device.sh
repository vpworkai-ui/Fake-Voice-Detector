#!/usr/bin/env bash
set -euo pipefail

PKG="${1:-com.vpsaker.fake_voice_detector}"
OUT_DIR="${2:-./data}"

mkdir -p "$OUT_DIR"
TMP_TAR="$OUT_DIR/dataset_samples.tar"

echo "[1/3] Exporting dataset_samples from app internal storage..."
adb exec-out run-as "$PKG" sh -c 'cd files && tar -cf - dataset_samples' > "$TMP_TAR"

echo "[2/3] Extracting tar..."
tar -xf "$TMP_TAR" -C "$OUT_DIR"

echo "[3/3] Done. Files extracted to: $OUT_DIR/dataset_samples"
