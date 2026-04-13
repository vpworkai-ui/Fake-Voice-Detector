# VoiceGuard — Deepfake Voice Detection trên Android

Ứng dụng Android phát hiện giả mạo giọng nói (Voice Spoofing / Deepfake Voice) sử dụng mô hình DNN 12KB chạy hoàn toàn **on-device** qua TensorFlow Lite.

> Luận văn Thạc sĩ — Nguyễn Kim Ngân (CHAT10) — Học viện Kỹ thuật Mật mã — GVHD: TS. Mai Đức Thọ

---

## Yêu cầu môi trường

| Công cụ | Phiên bản |
|---------|-----------|
| **JDK** | **17** (bắt buộc — JDK 18+ gây lỗi Kotlin compiler) |
| Android SDK | API 35 (compileSdk), minSdk 30 (Android 11+) |
| Android Studio | Ladybug trở lên |

> Nếu dùng JDK khác, chạy: `JAVA_HOME=$(/usr/libexec/java_home -v 17) ./gradlew assembleDebug`

---

## Build và chạy nhanh

```bash
# Clone
git clone <repo-url>
cd fake-voice-detector

# Build debug APK (không cần cấu hình thêm gì)
./gradlew assembleDebug

# Cài lên thiết bị/emulator đang kết nối
./gradlew installDebug
```

App sẽ chạy được **ngay lập tức** — mô hình TFLite đã được nhúng sẵn trong APK.

---

## Tính năng

- **Tab Phát hiện**: Ghi âm → phát hiện BONAFIDE / SPOOF on-device, hiển thị xác suất và hiệu năng (latency, RAM)
- **Tab Lịch sử**: Lịch sử phiên phân tích, xuất CSV
- **Tab Cài đặt**: Điều chỉnh ngưỡng spoof/ASV, kết nối ASV backend từ xa, thông tin mô hình

---

## Kiến trúc

```
presentation/   ← Jetpack Compose UI + ViewModel (MVI, StateFlow)
domain/         ← Use cases, Repository interfaces, Domain models
data/           ← AudioRecorder, FeatureExtractor, TFLite engine, DataStore
```

**Pipeline phát hiện on-device:**
1. Thu âm PCM 16kHz qua AudioRecord API
2. VAD (Voice Activity Detection) loại bỏ khoảng lặng
3. Trích xuất 8 đặc trưng âm thanh (RMS, ZCR, Peak, Crest…)
4. Chuẩn hóa và chạy mô hình TFLite 12KB
5. Ra quyết định: BONAFIDE / SPOOF → kết hợp ASV → ALLOW / REVIEW / BLOCK

---

## Mô hình AI

| Thông số | Giá trị |
|----------|---------|
| Kiến trúc | DNN: Dense(64,ReLU) → Dropout(0.2) → Dense(32,ReLU) → Dense(1,Sigmoid) |
| Tham số | 2.689 |
| Kích thước TFLite | 12 KB |
| Dữ liệu huấn luyện | VIVOS (bonafide) + mc_thu_hue (spoof) — 24.840 mẫu tiếng Việt |
| Accuracy | 98.23% |
| F1-Score | 98.23% |
| AUC | 0.9974 |
| EER | 1.93% |

File model: `app/src/main/assets/models/voice_spoof_detector.tflite`

---

## Cấu hình ASV Backend (tuỳ chọn)

Mặc định app hoạt động **offline** hoàn toàn. Để bật xác minh ASV từ xa, thêm vào `gradle.properties` (hoặc biến môi trường):

```properties
ASV_ENDPOINT=https://your-domain.com/api/asv/score
TELEMETRY_ENDPOINT=https://your-domain.com/api/telemetry/events
ASV_API_KEY=your_key_here
TELEMETRY_API_KEY=your_key_here
```

Hoặc cấu hình trực tiếp trong Tab Cài đặt của app.

### API contract

**Request** (POST JSON):
```json
{
  "spoofProbability": 0.21,
  "recordingDurationSec": 2.43,
  "sessionTimestampMs": 1710000000000
}
```

**Response**:
```json
{
  "asvScore": 0.84,
  "source": "remote"
}
```

---

## Ma trận quyết định

| CM (on-device) | ASV score | Quyết định |
|----------------|-----------|-----------|
| SPOOF | bất kỳ | **BLOCK** |
| BONAFIDE | ≥ 0.75 | **ALLOW** |
| BONAFIDE | 0.67 – 0.75 và spoof risk rất thấp | **REVIEW** |
| BONAFIDE | < 0.75 (các trường hợp còn lại) | **BLOCK** |

> Ngưỡng mặc định: `spoofThreshold = 0.50`, `asvThreshold = 0.75`. Có thể điều chỉnh trong **Tab Cài đặt**.

---

## Huấn luyện lại mô hình

Xem [TRAINING_GUIDE.md](TRAINING_GUIDE.md) để biết cách:
- Chuẩn bị dataset
- Huấn luyện mô hình DNN
- Xuất sang TFLite và cập nhật vào app

---

## Tài liệu kỹ thuật

- [docs/INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) — Hướng dẫn tích hợp backend
- [docs/BACKEND_REFERENCE.md](docs/BACKEND_REFERENCE.md) — API reference
- [ml/README.md](ml/README.md) — Pipeline huấn luyện ML
