# Voice Spoof Model Placement

Đặt model TensorFlow Lite vào file:

`app/src/main/assets/models/voice_spoof_detector.tflite`

Yêu cầu đầu vào hiện tại của app:
- Input shape: `[1, N]` (N >= 8)
- Feature order: `rms, meanAbs, zcr, peak, crestFactor, clippingRatio, dynamicRange, durationSec`

Đầu ra hỗ trợ:
- `[1, 1]`: spoof probability hoặc logit
- `[1, 2]`: `[bonafide, spoof]` (probabilities hoặc logits)

Nếu model chưa có, app sẽ dùng heuristic fallback để demo luồng hoạt động end-to-end.
