# Fake Voice Detector (Android)

Ứng dụng Android phát hiện giả mạo giọng nói (voice spoofing detection) để bổ sung lớp bảo vệ cho hệ thống xác thực giọng nói (ASV).

## Kiến trúc

- `presentation`: Compose UI + ViewModel + state
- `domain`: model, repository contract, use case
- `data`: microphone recorder, feature extractor, detector engine (TFLite + fallback)

Luồng xử lý:
1. Xin quyền microphone.
2. Ghi âm PCM 16kHz.
3. Trích xuất 8 đặc trưng âm thanh.
4. Chạy model TFLite (nếu có) hoặc heuristic fallback.
5. Trả kết quả `BONAFIDE/SPOOF` + confidence.

## Tích hợp model anti-spoof thật

Đặt model tại:

`app/src/main/assets/models/voice_spoof_detector.tflite`

Yêu cầu input/output tham khảo ở `app/src/main/assets/models/README.md`.

## Build và chạy

```bash
./gradlew test
./gradlew assembleDebug
```

## Lưu ý bảo mật thực tế

- Heuristic fallback chỉ để demo pipeline, không dùng production.
- Cần model anti-spoof được huấn luyện bài bản (ASVspoof/your data).
- Nên thêm liveness checks và fuse với ASV score để giảm false acceptance.
