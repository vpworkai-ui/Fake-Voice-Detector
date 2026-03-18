# Fake Voice Detector (Android)

Ứng dụng Android phát hiện giả mạo giọng nói (voice spoofing detection) nhằm bổ sung lớp bảo vệ cho hệ thống xác thực giọng nói (ASV).

## Điểm hoàn thiện hiện tại

- Kiến trúc `data/domain/presentation` rõ ràng, dễ mở rộng.
- Runtime suy luận dùng `Google LiteRT` (on-device).
- Ghi âm microphone PCM 16kHz + trích xuất đặc trưng.
- Fusion decision với ASV score: `ALLOW / REVIEW / BLOCK`.
- Hỗ trợ gọi ASV backend qua HTTP (header auth bằng API key nếu cấu hình).
- Release hardening: bản release bắt buộc model anti-spoof thật + ASV backend thật (không heuristic/manual fallback).
- Calibration ngưỡng ngay trên app:
  - `spoof threshold`
  - `ASV threshold`
- Lưu cấu hình ngưỡng bằng `DataStore` (không mất sau khi tắt app).
- Lịch sử phiên phân tích gần nhất để audit nhanh.
- Quality gate đầu vào (duration/volume/clipping) trước khi ra quyết định.
- Telemetry queue cục bộ + retry upload (store-and-forward).

## Kiến trúc

- `presentation`: Compose UI + ViewModel + state
- `domain`: model, repository contract, use case
- `data`: microphone recorder, feature extractor, detector engine LiteRT, DataStore config

Luồng xử lý:
1. Xin quyền microphone.
2. Thu âm giọng nói.
3. Trích xuất đặc trưng âm thanh.
4. Chạy model LiteRT.
5. Kết hợp với ASV score để đưa ra quyết định fusion.

## Cấu hình tích hợp backend

Thiết lập các biến sau trong `gradle.properties` hoặc environment variables:

- `ASV_ENDPOINT`
- `TELEMETRY_ENDPOINT`
- `ASV_API_KEY`
- `TELEMETRY_API_KEY`

Ví dụ:

```properties
ASV_ENDPOINT=https://your-domain.com/api/asv/score
TELEMETRY_ENDPOINT=https://your-domain.com/api/telemetry/events
ASV_API_KEY=replace_me
TELEMETRY_API_KEY=replace_me
```

## ASV Backend Integration

Trên UI:
- Bật `Use remote ASV backend`.
- Nhập `ASV endpoint URL`.

App sẽ gọi `POST` JSON tới endpoint:

```json
{
  "spoofProbability": 0.21,
  "recordingDurationSec": 2.43,
  "sessionTimestampMs": 1710000000000
}
```

Backend cần trả về tối thiểu:

```json
{
  "asvScore": 0.84,
  "source": "remote"
}
```

Ở `release`, endpoint placeholder (`example.com` / `localhost`) sẽ bị chặn theo fail-safe policy.

## Telemetry Local Log

Mỗi phiên xác thực sẽ được ghi local JSONL tại:

`<app_files_dir>/telemetry/voice_auth_events.jsonl`

Event chờ upload được giữ tại:

`<app_files_dir>/telemetry/voice_auth_pending.jsonl`

Các trường chính gồm:
- `timestampMs`
- `spoofProbability`
- `asvScore`
- `decision`
- `reason`
- `asvSource`
- `asvLatencyMs`
- `modelName`
- `recordingDurationSec`

Ứng dụng sẽ tự thử upload pending events tới endpoint telemetry suy ra từ ASV endpoint:

- nếu ASV endpoint là `/api/asv/score`
- thì telemetry endpoint mặc định là `/api/telemetry/events`

## Tích hợp model anti-spoof thật

Đặt model tại:

`app/src/main/assets/models/voice_spoof_detector.tflite`

Yêu cầu input/output tham khảo ở:

`app/src/main/assets/models/README.md`

## Build và chạy

```bash
./gradlew testDebugUnitTest
./gradlew assembleDebug
```

## Tài liệu triển khai

- [INTEGRATION_GUIDE.md](/Users/phucit/Desktop/Work/KMP/Repos/fake_voice_detector/docs/INTEGRATION_GUIDE.md)
- [BACKEND_REFERENCE.md](/Users/phucit/Desktop/Work/KMP/Repos/fake_voice_detector/docs/BACKEND_REFERENCE.md)
