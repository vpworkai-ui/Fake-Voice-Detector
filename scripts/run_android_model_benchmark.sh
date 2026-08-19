#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-external_holdout}"
MODELS="${MODELS:-cross_scale_attention_lite,aasist_lite,cbam_resnet_lite}"
THRESHOLD="${THRESHOLD:-0.25}"
PROGRESS_EVERY="${PROGRESS_EVERY:-100}"
SEED="${SEED:-42}"
MIX_PER_CLASS="${MIX_PER_CLASS:-150}"

REMOTE_BASE="/sdcard/Android/media/com.vpsaker.fake_voice_detector/benchmark"
REMOTE_DATASET_ROOT="$REMOTE_BASE/benchmark_dataset"
REMOTE_MANIFEST="$REMOTE_BASE/benchmark_manifest.tsv"
REMOTE_OUTPUT="$REMOTE_BASE/android_runtime_benchmark.json"

LOCAL_ARTIFACT_DIR="$ROOT_DIR/ml/artifacts/android_runtime_benchmark"
LOCAL_MANIFEST="$LOCAL_ARTIFACT_DIR/benchmark_manifest.tsv"
LOCAL_OUTPUT="$LOCAL_ARTIFACT_DIR/android_runtime_benchmark.json"
LOCAL_STAGE_ROOT="$LOCAL_ARTIFACT_DIR/staged_dataset"

mkdir -p "$LOCAL_ARTIFACT_DIR"

export LOCAL_DATASET_ROOT SEED MIX_PER_CLASS LOCAL_MANIFEST LOCAL_STAGE_ROOT

case "$MODE" in
  external_holdout)
    LOCAL_DATASET_ROOT="$ROOT_DIR/data/external_vietnamese_test"
    REMOTE_DATASET="$REMOTE_DATASET_ROOT/external_vietnamese_test"
    python3 - <<'PY' > "$LOCAL_MANIFEST"
from pathlib import Path
import os, random

root = Path(os.environ["LOCAL_DATASET_ROOT"])
seed = int(os.environ["SEED"])
mix_per_class = int(os.environ["MIX_PER_CLASS"])

for label in ("bonafide", "spoof"):
    files = sorted((root / label).glob("*.wav"))
    rels = [f.relative_to(root).as_posix() for f in files]
    random.Random(seed).shuffle(rels)
    for rel in rels[mix_per_class:]:
        print(f"{rel}\t{label}")
PY
    ;;
  external_all)
    LOCAL_DATASET_ROOT="$ROOT_DIR/data/external_vietnamese_test"
    REMOTE_DATASET="$REMOTE_DATASET_ROOT/external_vietnamese_test"
    python3 - <<'PY' > "$LOCAL_MANIFEST"
from pathlib import Path
import os

root = Path(os.environ["LOCAL_DATASET_ROOT"])
for label in ("bonafide", "spoof"):
    for file in sorted((root / label).glob("*.wav")):
        print(f"{file.relative_to(root).as_posix()}\t{label}")
PY
    ;;
  internal_all)
    LOCAL_DATASET_ROOT="$ROOT_DIR/data/dataset_samples"
    REMOTE_DATASET="$REMOTE_DATASET_ROOT/dataset_samples"
    python3 - <<'PY' > "$LOCAL_MANIFEST"
from pathlib import Path
import os

root = Path(os.environ["LOCAL_DATASET_ROOT"])
for label in ("bonafide", "spoof"):
    for file in sorted((root / label).glob("*.wav")):
        print(f"{file.relative_to(root).as_posix()}\t{label}")
PY
    ;;
  *)
    echo "Unsupported mode: $MODE" >&2
    echo "Supported: external_holdout | external_all | internal_all" >&2
    exit 1
    ;;
esac

echo "[1/6] Building debug app APK"
cd "$ROOT_DIR"
./gradlew :app:assembleDebug >/dev/null

echo "      Staging only manifest-selected wav files"
rm -rf "$LOCAL_STAGE_ROOT"
mkdir -p "$LOCAL_STAGE_ROOT"
python3 - <<'PY'
from pathlib import Path
import os, shutil

dataset_root = Path(os.environ["LOCAL_DATASET_ROOT"])
manifest_path = Path(os.environ["LOCAL_MANIFEST"])
stage_root = Path(os.environ["LOCAL_STAGE_ROOT"])

for line in manifest_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    rel = line.split('\t', 1)[0]
    src = dataset_root / rel
    dst = stage_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)
PY

echo "[2/6] Installing debug APK on connected device"
adb install -r "$ROOT_DIR/app/build/outputs/apk/debug/app-debug.apk" >/dev/null

echo "[3/6] Preparing device folders"
adb shell "rm -rf '$REMOTE_DATASET_ROOT' && mkdir -p '$REMOTE_DATASET_ROOT' '$REMOTE_BASE'" >/dev/null
adb shell "rm -f '$REMOTE_OUTPUT' '$REMOTE_MANIFEST'" >/dev/null

echo "[4/6] Pushing dataset + manifest to device"
adb push "$LOCAL_STAGE_ROOT" "$REMOTE_DATASET_ROOT" >/dev/null
adb push "$LOCAL_MANIFEST" "$REMOTE_MANIFEST" >/dev/null

echo "[5/6] Launching in-app runtime benchmark activity ($MODE)"
adb shell am start -n com.vpsaker.fake_voice_detector/.debug.RuntimeBenchmarkActivity \
  --es datasetRoot "$REMOTE_DATASET" \
  --es manifestPath "$REMOTE_MANIFEST" \
  --es outputPath "$REMOTE_OUTPUT" \
  --es threshold "$THRESHOLD" \
  --es progressEvery "$PROGRESS_EVERY" \
  --es models "$MODELS" >/dev/null

echo "      Waiting for benchmark JSON from app runtime..."
for _ in $(seq 1 1800); do
  if adb shell "test -f '$REMOTE_OUTPUT'" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! adb shell "test -f '$REMOTE_OUTPUT'" >/dev/null 2>&1; then
  echo "Benchmark timed out before producing $REMOTE_OUTPUT" >&2
  exit 1
fi

echo "[6/6] Pulling benchmark JSON"
adb pull "$REMOTE_OUTPUT" "$LOCAL_OUTPUT" >/dev/null

echo
echo "Saved benchmark output: $LOCAL_OUTPUT"
