# Fake Voice Detector (Android)

Ứng dụng Android phát hiện giả mạo giọng nói (voice spoofing detection) nhằm bổ sung lớp bảo vệ cho hệ thống xác thực giọng nói (ASV).

## Điểm hoàn thiện hiện tại

- Kiến trúc `data/domain/presentation` rõ ràng, dễ mở rộng.
- Runtime suy luận dùng `Google LiteRT` (on-device).
- Ghi âm microphone PCM 16kHz + trích xuất đặc trưng.
- Fusion decision với ASV score: `ALLOW / REVIEW / BLOCK`.
- Calibration ngưỡng ngay trên app:
  - `spoof threshold`
  - `ASV threshold`
- Lưu cấu hình ngưỡng bằng `DataStore` (không mất sau khi tắt app).
- Lịch sử phiên phân tích gần nhất để audit nhanh.

## Kiến trúc

- `presentation`: Compose UI + ViewModel + state
- `domain`: model, repository contract, use case
- `data`: microphone recorder, feature extractor, detector engine (LiteRT + fallback), DataStore config

Luồng xử lý:
1. Xin quyền microphone.
2. Thu âm giọng nói.
3. Trích xuất đặc trưng âm thanh.
4. Chạy model LiteRT (nếu có) hoặc heuristic fallback.
5. Kết hợp với ASV score để đưa ra quyết định fusion.

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

## Lưu ý production

- Heuristic fallback chỉ để giữ pipeline chạy khi chưa có model thật.
- Cần model anti-spoof huấn luyện bài bản trên dữ liệu phù hợp miền nghiệp vụ.
- Nên triển khai thêm step-up verification khi kết quả `REVIEW`.
- Nên đẩy log phiên xác thực lên backend để theo dõi drift và tuning threshold theo thời gian.
