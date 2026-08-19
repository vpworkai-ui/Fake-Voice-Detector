#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ADB="${ADB:-$HOME/Library/Android/sdk/platform-tools/adb}"
APK_PATH="${APK_PATH:-$ROOT_DIR/app/build/outputs/apk/debug/app-debug.apk}"
APP_ID="${APP_ID:-com.vpsaker.fake_voice_detector}"
ACTIVITY="${ACTIVITY:-com.vpsaker.fake_voice_detector.MainActivity}"
DEVICE_VIDEO_PATH="${DEVICE_VIDEO_PATH:-/sdcard/voiceguard_demo.mp4}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/tmp/video_review}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_PATH="$OUTPUT_DIR/voiceguard_demo_${TIMESTAMP}.mp4"

if [[ ! -x "$ADB" ]]; then
  echo "ADB not found at: $ADB" >&2
  exit 1
fi

if [[ ! -f "$APK_PATH" ]]; then
  echo "APK not found at: $APK_PATH" >&2
  echo "Build it first with: ./gradlew app:assembleDebug" >&2
  exit 1
fi

DEVICE_COUNT="$($ADB devices | awk 'NR>1 && $2=="device" {count++} END {print count+0}')"
if [[ "$DEVICE_COUNT" -eq 0 ]]; then
  echo "No authorized Android device detected." >&2
  echo "Connect phone, enable USB debugging, accept the RSA prompt, then retry." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "Installing debug APK..."
$ADB install -r "$APK_PATH"

echo "Clearing old demo video on device..."
$ADB shell rm -f "$DEVICE_VIDEO_PATH" || true

echo "Launching app..."
$ADB shell am start -n "$APP_ID/$ACTIVITY"

echo
echo "Recording will start now."
echo "Perform the demo on the phone."
echo "Press Enter here when you want to stop recording."

$ADB shell screenrecord "$DEVICE_VIDEO_PATH" >/tmp/voiceguard_screenrecord.log 2>&1 &
REC_PID=$!

read -r

kill -INT "$REC_PID" 2>/dev/null || true
wait "$REC_PID" 2>/dev/null || true

echo "Pulling video from device..."
$ADB pull "$DEVICE_VIDEO_PATH" "$OUTPUT_PATH"

echo "Saved demo video to: $OUTPUT_PATH"

