# VoiceGuard — Deepfake Voice Detection trên Android

Ứng dụng Android phát hiện giả mạo giọng nói (Voice Spoofing / Deepfake Voice) sử dụng mô hình **Cross-Scale Attention Lite (spectrogram + 8 đặc trưng acoustic, ~42KB)** chạy hoàn toàn **on-device** qua TensorFlow Lite.

> Luận văn Thạc sĩ — Nguyễn Kim Ngân (CHAT10) — Học viện Kỹ thuật Mật mã — GVHD: TS. Mai Đức Thọ

---

## Yêu cầu môi trường

| Công cụ | Phiên bản |
|---------|-----------|
| **JDK** | **17** (bắt buộc — JDK 18+ gây lỗi Kotlin compiler) |
| Android SDK | API 36 (compileSdk/targetSdk), minSdk 24 (Android 7.0+) |
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

- **Tab Phát hiện**: Ghi âm → VAD quality gate → phát hiện BONAFIDE / SPOOF on-device, hiển thị xác suất và hiệu năng (latency, RAM)
- **Tab Lịch sử**: Lịch sử phiên phân tích, xuất CSV
- **Tab Cài đặt**: Điều chỉnh ngưỡng spoof/ASV, kết nối ASV backend từ xa, thông tin mô hình

---

## Kiến trúc

```
presentation/   ← Jetpack Compose UI + ViewModel (MVI, StateFlow)
domain/         ← Use cases, Repository interfaces, Domain models
data/           ← AudioRecorder, AudioQualityGate, FeatureExtractor, TFLite engine, DataStore
```

**Pipeline phát hiện on-device (model deploy hiện tại):**
1. Thu âm PCM 16kHz qua `AudioSource.VOICE_RECOGNITION` (noise suppression tự động)
2. `AudioQualityGate` — từ chối nếu RMS < -45dBFS, active speech < 1s, SNR < 8dB
3. Tạo **log-Mel spectrogram** và trích xuất **8 đặc trưng acoustic thủ công**: `RMS, MeanAbs, ZCR, Peak, CrestFactor, ClippingRatio, DynamicRange, DurationSec`
4. Chạy mô hình dual-input TFLite ~42KB: `spectrogram + acoustic features`
5. Ra quyết định: BONAFIDE / SPOOF → kết hợp ASV → ALLOW / REVIEW / BLOCK

Lưu ý về tên đặc trưng thứ 8:
- Runtime Android hiện dùng `DurationSec` = tổng thời lượng đoạn audio sau chuẩn hóa/padding.
- Một số báo cáo hoặc script huấn luyện cũ trong repo vẫn gọi đặc trưng này là `ActiveDuration` hoặc `active_duration_sec`; đó là tên lịch sử, không phải hành vi runtime hiện tại của app.

---

## Mô hình AI (deploy hiện tại)

| Thông số | Giá trị |
|----------|---------|
| Kiến trúc | **Cross-Scale Attention Lite** dual-input: `log-Mel spectrogram + 8 acoustic features` |
| Tham số | **9.313** |
| Kích thước TFLite | **42.2 KB** |
| Đầu vào | Spectrogram + **8** đặc trưng acoustic thủ công |
| Dữ liệu huấn luyện | VIVOS + mc_thu_hue (24.840 nội bộ) + 800 mẫu ngoài nguồn (400 bonafide + 400 spoof) |
| Internal Accuracy | **98.79%** |
| Internal F1 | **98.80%** |
| External Accuracy (thr=0.25) | **85.29%** |
| External Recall Spoof | **97.65%** |
| External F1 | **86.91%** |
| Latency pipeline | **311ms** |

File model: `app/src/main/assets/models/voice_spoof_detector.tflite`

> File model đang được bundle trong app có kích thước thực tế khoảng **42.2 KB** (`43220` bytes), khớp với nhánh `cross_scale_attention_lite`.

### Lịch sử model

| Phiên bản | Đặc trưng | TFLite | External Acc | EER |
|-----------|-----------|--------|-------------|-----|
| v1 — DNN gốc | 8 | 12 KB | ~50% | — |
| **v1.5 — cross_scale+spec** *(deploy hiện tại)* | **8+spec** | **42.2 KB** | **85.29%** | **18.24%** |
| v2 — DNN+MFCC *(nhánh nghiên cứu / train lại)* | 21 | 54 KB | 91.67% | 9.33% |

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
  "spoofProbability": 0.021,
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

| CM on-device (cross-scale deploy) | ASV score | Quyết định |
|----------------------------------|-----------|-----------|
| score ≥ **0.25** (SPOOF) | bất kỳ | **BLOCK** |
| score < 0.25 (BONAFIDE) | ≥ 0.75 | **ALLOW** |
| score ≤ 0.1375 (BONAFIDE rất sạch) | 0.67 – 0.75 | **REVIEW** |
| score < 0.25 (BONAFIDE) | < 0.75 (các trường hợp còn lại) | **BLOCK** |

> Ngưỡng mặc định: `spoofThreshold = 0.25`, `asvThreshold = 0.75`. Có thể điều chỉnh trong **Tab Cài đặt**.
>
> **Lý do threshold = 0.25:** Đây là ngưỡng đang dùng trong app và các benchmark/report tuần hiện tại để đối chiếu thống nhất giữa runtime, slide và báo cáo.

---

## Huấn luyện lại mô hình

Xem [docs/training/README.md](docs/training/README.md) để biết cách:
- Chuẩn bị dataset
- Huấn luyện nhánh deploy `cross_scale_attention_lite` trong các script benchmark/mix-retrain của thư mục `ml/`
- Hoặc trích xuất 21 đặc trưng: `python ml/extract_features_v2.py`
- Huấn luyện nhánh DNN v2 (21 đặc trưng): `python ml/train_spoof_model_v2.py --from-cache`
- Xuất sang TFLite và cập nhật vào app

---

## Tài liệu kỹ thuật

- [docs/technical/INTEGRATION_GUIDE.md](docs/technical/INTEGRATION_GUIDE.md) — Hướng dẫn tích hợp backend
- [docs/technical/BACKEND_REFERENCE.md](docs/technical/BACKEND_REFERENCE.md) — API reference
- [docs/technical/3_3_DANH_GIA_HIEU_NANG_HE_THONG.md](docs/technical/3_3_DANH_GIA_HIEU_NANG_HE_THONG.md) — Đánh giá hiệu năng hệ thống
- [ml/README.md](ml/README.md) — Pipeline huấn luyện ML
- [docs/training/README.md](docs/training/README.md) — Hướng dẫn training đầy đủ
