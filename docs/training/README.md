# Hướng dẫn Huấn luyện Mô hình Anti-Spoof

Tài liệu này mô tả đầy đủ quy trình từ chuẩn bị dataset → huấn luyện mô hình → triển khai lên Android app.

---

## Tổng quan kiến trúc

```
Dataset (WAV files)
    │
    ▼
ml/prepare_dataset.py     ← tổ chức data vào bonafide/ và spoof/
    │
    ▼
ml/train_spoof_model.py   ← trích xuất 8 đặc trưng + train DNN → export .tflite
    │
    ▼
app/src/main/assets/models/voice_spoof_detector.tflite   ← Android app đọc trực tiếp
    │
    ▼
Android App (TFLiteSpoofDetectorEngine.kt)   ← inference on-device
```

---

## Lưu ý về Dataset

> **Dataset không được đẩy lên Git** do kích thước quá lớn (~42GB tổng).
> App Android vẫn chạy bình thường — model TFLite đã được compile sẵn trong repo.
> Chỉ cần tải dataset nếu muốn **huấn luyện lại** mô hình.

| Thư mục | Nội dung | Kích thước | Nguồn |
|---------|----------|------------|-------|
| `resources/mc_thu_hue_fix_char/` | Dataset spoof (TTS tiếng Việt) | ~11GB | Liên hệ tác giả |
| `data/dataset_samples/bonafide/` | Dataset bonafide (VIVOS) | ~31GB | [ailab.hcmus.edu.vn/vivos](https://ailab.hcmus.edu.vn/vivos) |

Sau khi tải về, đặt đúng cấu trúc thư mục rồi chạy `ml/prepare_dataset.py` (xem bên dưới).

---

## Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|---|---|
| Python | 3.10+ (khuyến nghị 3.13 từ Homebrew) |
| TensorFlow | 2.18+ (cài qua pip) |
| Android Studio | Bumblebee+ / JDK 17 |
| Dung lượng dataset | Tối thiểu ~100 file WAV mỗi lớp |

---

## Bước 1 — Cài môi trường Python

```bash
cd /path/to/fake_voice_detector/ml

# Tạo virtualenv (dùng Python 3.13 từ Homebrew trên macOS)
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# hoặc: .venv\Scripts\activate     # Windows

# Cài thư viện
pip install numpy scikit-learn tensorflow
```

---

## Bước 2 — Chuẩn bị Dataset

Có **3 lựa chọn** tùy vào dữ liệu bạn có:

---

### Lựa chọn A — Kaggle "The Fake or Real Dataset" ⭐ (khuyến nghị cho đề tài)

Đây là dataset chuẩn, được dùng phổ biến trong nghiên cứu chống giả mạo giọng nói.

**Tải dataset:**

1. Đăng ký tài khoản tại [kaggle.com](https://www.kaggle.com)
2. Vào trang: `https://www.kaggle.com/datasets/mohammedabdeldayem/the-fake-or-real-dataset`
3. Nhấn **Download** → tải file `archive.zip` (khoảng 4-16 GB tùy bản)
4. Giải nén ra thư mục, ví dụ: `~/Downloads/for-norm/`

Cấu trúc sau khi giải nén:
```
for-norm/
  training/
    real/   ← bonafide WAV files
    fake/   ← spoof WAV files
  validation/
    real/
    fake/
  testing/
    real/
    fake/
```

**Chuẩn bị dataset:**

```bash
cd /path/to/fake_voice_detector

python ml/prepare_dataset.py \
  --mode kaggle \
  --source ~/Downloads/for-norm \
  --output data/dataset_samples

# (Tùy chọn) Giới hạn số file mỗi lớp để train nhanh hơn:
python ml/prepare_dataset.py \
  --mode kaggle \
  --source ~/Downloads/for-norm \
  --output data/dataset_samples \
  --limit 2000
```

---

### Lựa chọn B — Dataset tự thu âm từ app Android

Dùng tính năng "Thu thập Dataset" trong app để ghi âm giọng thật (bonafide) và phát lại TTS/AI (spoof), sau đó export ra máy tính.

**Export file từ thiết bị Android:**

```bash
# Kết nối điện thoại qua USB (bật ADB)
adb pull /sdcard/Android/data/com.vpsaker.fake_voice_detector/files/dataset ./data/device_dataset

# Cấu trúc sau khi pull:
# data/device_dataset/
#   bonafide/   ← ghi âm trực tiếp
#   spoof/      ← phát lại TTS/AI qua loa
```

**Chuẩn bị dataset:**

```bash
python ml/prepare_dataset.py \
  --mode custom \
  --bonafide-src data/device_dataset/bonafide \
  --spoof-src    data/device_dataset/spoof \
  --output       data/dataset_samples
```

---

### Lựa chọn C — Demo mode (chỉ kiểm thử pipeline)

> ⚠️ **CẢNH BÁO:** Chế độ này dùng tín hiệu tổng hợp làm bonafide.
> Model train ra **KHÔNG có giá trị thực tế** và **KHÔNG dùng được trong báo cáo đề tài**.
> Chỉ dùng để xác nhận pipeline end-to-end chạy đúng.

```bash
# Dùng TTS trong resources/ làm spoof + tạo tín hiệu tổng hợp làm bonafide
python ml/prepare_dataset.py \
  --mode demo \
  --spoof-src resources/mc_thu_hue_fix_char/wavs \
  --output data/dataset_samples \
  --demo-n-spoof   400 \
  --demo-n-bonafide 400
```

---

## Bước 3 — Huấn luyện mô hình

```bash
cd /path/to/fake_voice_detector
source ml/.venv/bin/activate

python ml/train_spoof_model.py \
  --dataset-root data/dataset_samples \
  --output-dir   ml/artifacts \
  --epochs       30 \
  --batch-size   32 \
  --seed         42
```

**Các tham số quan trọng:**

| Tham số | Mô tả | Mặc định |
|---|---|---|
| `--dataset-root` | Thư mục chứa `bonafide/` và `spoof/` | `data/dataset_samples` |
| `--output-dir` | Nơi lưu model và report | `ml/artifacts` |
| `--epochs` | Số epoch huấn luyện tối đa | `30` |
| `--batch-size` | Kích thước batch | `16` |
| `--target-sr` | Sample rate chuẩn hóa (Hz) | `16000` |
| `--seed` | Seed ngẫu nhiên (tái lặp kết quả) | `42` |

**Output sau khi train:**

```
ml/artifacts/
  voice_spoof_detector.keras   ← Keras model đầy đủ
  voice_spoof_detector.tflite  ← Model đã tối ưu cho Android ← CẦN FILE NÀY
  feature_stats.npy            ← Mean/std dùng để chuẩn hóa feature
  report.json                  ← Kết quả đánh giá (Accuracy, F1, ...)
```

**Kết quả thực tế trên dataset VIVOS + mc_thu_hue (24.840 mẫu):**

```json
{
  "val":  { "accuracy": 0.9839, "precision": 0.9810, "recall": 0.9869, "f1": 0.9839, "count": 3975 },
  "test": { "accuracy": 0.9823, "precision": 0.9807, "recall": 0.9839, "f1": 0.9823, "count": 4968 },
  "dataset": { "total": 24840, "bonafide": 12420, "spoof": 12420, "failed_files": [] }
}
```

### Huấn luyện 3 model mới với augmentation + acoustic features

Sau khi khảo sát các model mới và test ngoài nguồn, pipeline benchmark có thêm chế độ kết hợp deep model với 8 đặc trưng âm thanh trong luận văn. Đây là hướng nên dùng để so sánh nghiệm thu vì vẫn giữ được khả năng triển khai Android, nhưng bớt phụ thuộc vào khác biệt nguồn dữ liệu.

```bash
python ml/benchmark_android_models.py \
  --dataset-root data/dataset_samples \
  --output-dir ml/artifacts/android_model_benchmark_acoustic_augmented \
  --models cross_scale_attention_lite,aasist_lite,cbam_resnet_lite \
  --epochs 12 \
  --batch-size 32 \
  --test-count 2000 \
  --val-count 2284 \
  --augment \
  --acoustic-features \
  --seed 42
```

Đánh giá trên dữ liệu tiếng Việt khác nguồn:

```bash
python ml/evaluate_external_models.py \
  --models-dir ml/artifacts/android_model_benchmark_acoustic_augmented \
  --external-root data/external_vietnamese_test \
  --output-dir ml/artifacts/external_evaluation_vietnamese_acoustic_augmented \
  --limit-per-class 1000 \
  --batch-size 32
```

Chi tiết lý do, feature sử dụng và cách so sánh trước/sau nằm ở [ACOUSTIC_IMPROVEMENT_PLAN.md](ACOUSTIC_IMPROVEMENT_PLAN.md).

---

## Bước 3.5 — Ablation Study (theo yêu cầu GVHD)

Chứng minh tại sao cần **đúng 8 đặc trưng** (không phải 5, 6 hay 15) bằng cách bỏ từng đặc trưng và đo độ giảm hiệu năng:

```bash
cd /path/to/fake_voice_detector
source ml/.venv/bin/activate

python ml/ablation_study.py \
  --dataset-root data/dataset_samples \
  --epochs 30 \
  --seed 42
```

**Output (`ml/artifacts/ablation/`):**

| File | Nội dung |
|------|----------|
| `ablation_results.json` | Kết quả đầy đủ tất cả thí nghiệm |
| `ablation_summary.md` | Bảng markdown sẵn dùng cho luận văn |
| `ablation_chart.png` | Biểu đồ cột: tầm quan trọng từng đặc trưng + đường progressive |

> Script thực hiện **10 lần huấn luyện**: 1 baseline (cả 8) + 8 leave-one-out + progressive addition.

---

## Bước 3.6 — t-SNE Visualization (theo yêu cầu GVHD)

Dùng t-SNE để **visualize data record** — quan sát xem bonafide/spoof tách nhau không, và dữ liệu nội bộ vs ngoài nguồn có cùng phân phối không:

```bash
python ml/tsne_visualization.py \
  --internal-root data/dataset_samples \
  --external-root data/external_vietnamese_test \
  --limit-internal 2000 \
  --limit-external 1000 \
  --seed 42
```

**Output (`ml/artifacts/tsne/`):**

| File | Nội dung |
|------|----------|
| `tsne_label.png` | Phân bố t-SNE màu theo nhãn (bonafide / spoof) |
| `tsne_source.png` | Phân bố t-SNE màu theo nguồn (nội bộ / ngoài) |
| `tsne_combined.png` | Kết hợp: hình=nguồn, màu=nhãn — thấy rõ domain shift |
| `tsne_feature_density.png` | Histogram 8 đặc trưng: bonafide vs spoof |
| `tsne_embedding.csv` | Tọa độ t-SNE + đặc trưng từng mẫu (audit) |

> **Domain shift** thể hiện rõ khi cluster internal và external không chồng lên nhau — đây là lý do external accuracy thấp.

---

## Bước 3.7 — Sinh biểu đồ đánh giá (ROC, AUC, EER, Confusion Matrix)

Sau khi train xong, chạy thêm script này để sinh biểu đồ luận văn và tính AUC/EER:

```bash
cd /path/to/fake_voice_detector
source ml/.venv/bin/activate

python ml/generate_charts.py
```

> **Ghi chú:** Đây là bước 3.7 (đánh số lại sau khi thêm ablation và t-SNE).

**Output (`ml/charts/`):**

| File | Nội dung |
|------|----------|
| `training_curves.png` | Loss & Accuracy theo từng epoch |
| `confusion_matrix.png` | Ma trận nhầm lẫn trên test set |
| `roc_curve.png` | ROC Curve + **AUC** + **EER** |
| `pr_curve.png` | Precision-Recall Curve |
| `feature_distributions.png` | Phân phối 8 đặc trưng: Bonafide vs Spoof |
| `metrics_summary.png` | Bảng tổng hợp chỉ số |

> **Ghi chú:** AUC và EER chỉ được tính ở bước này (không có trong `report.json`).  
> Kết quả trên dataset 24.840 mẫu: **AUC = 0.9974**, **EER = 1.93%**.

Script yêu cầu `ml/artifacts/` và `data/dataset_samples/` đã tồn tại (chạy sau bước 2 và 3).

---

## Bước 4 — Triển khai model lên Android

**Copy file `.tflite` vào assets:**

```bash
cp ml/artifacts/voice_spoof_detector.tflite \
   app/src/main/assets/models/voice_spoof_detector.tflite
```

**Build lại app:**

```bash
# macOS — dùng JDK 17 (JDK 25 không tương thích với Kotlin compiler hiện tại)
JAVA_HOME=/Library/Java/JavaVirtualMachines/openjdk-17.jdk/Contents/Home \
  ./gradlew assembleDebug

# Cài lên thiết bị (cần bật ADB)
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

---

## Bước 5 — Kiểm tra kết quả trên app

1. Mở app trên Android
2. Nhấn **Bắt Đầu Ghi Âm** → nói vào microphone
3. Nhấn **Dừng & Phân Tích**
4. Quan sát kết quả:
   - `Engine: tflite` = đang dùng model AI thật (thay vì heuristic fallback)
   - Xác suất giả mạo và quyết định ALLOW/REVIEW/BLOCK

---

## Hiểu 8 đặc trưng âm thanh

Script `train_spoof_model.py` trích xuất 8 đặc trưng từ tín hiệu PCM 16kHz:

| # | Tên | Mô tả | Ý nghĩa phân biệt |
|---|---|---|---|
| 1 | RMS | Năng lượng trung bình (căn bậc 2 giá trị bình phương) | TTS thường có RMS ổn định bất thường |
| 2 | MeanAbs | Biên độ tuyệt đối trung bình | Liên quan đến âm lượng tổng thể |
| 3 | ZCR | Zero Crossing Rate — tần suất tín hiệu đổi dấu | TTS có ZCR đặc trưng khác giọng thật |
| 4 | Peak | Giá trị biên độ lớn nhất | Phát hiện clipping hoặc replay attack |
| 5 | CrestFactor | Tỉ lệ Peak / RMS | Phản ánh cấu trúc động của tín hiệu |
| 6 | ClippingRatio | Tỉ lệ mẫu > 98% biên độ | Dấu hiệu replay qua loa ngoài |
| 7 | DynamicRange | Khoảng biến thiên max − min | Giọng thật có dynamic range tự nhiên hơn |
| 8 | Duration | Thời lượng đoạn âm (giây) | Ảnh hưởng đến độ tin cậy các đặc trưng |

---

## Kiến trúc mô hình AI

```
Input: [batch, 8]   ← 8 đặc trưng đã chuẩn hóa (z-score)
    │
Dense(64, ReLU)
    │
Dropout(0.2)        ← chống overfitting
    │
Dense(32, ReLU)
    │
Dense(1)            ← logit (sigmoid → xác suất spoof)
    │
Output: float ∈ [0, 1]   ← xác suất giả mạo
```

- **Loss:** Binary Cross-Entropy (from logits)
- **Optimizer:** Adam (lr = 0.001)
- **Early stopping:** patience = 6 epoch, monitor val_loss
- **Tỷ lệ split:** 60% train / 20% validation / 20% test

---

## Câu hỏi thường gặp

**Q: Accuracy = 1.0 có phải overfitting không?**

A: Với demo dataset (tín hiệu tổng hợp vs TTS), 2 lớp quá khác nhau nên accuracy 100% là bình thường — không có giá trị thực tế. Khi dùng Kaggle FOR dataset với dữ liệu thật, accuracy thường đạt 85–95%.

**Q: Cần bao nhiêu dữ liệu?**

A: Tối thiểu ~200 file/lớp để mô hình học được phân phối. Khuyến nghị 1000+ file/lớp cho kết quả tốt. Dataset Kaggle FOR có ~80.000 file.

**Q: App hiển thị "heuristic" thay vì "tflite"?**

A: File `voice_spoof_detector.tflite` chưa có trong `app/src/main/assets/models/`. Chạy lại bước 4.

**Q: Tôi có thể thêm đặc trưng khác không?**

A: Có, nhưng cần sửa cả `AudioFeatureExtractor.kt` (Android) và `extract_features()` trong `train_spoof_model.py` để đảm bảo feature order khớp nhau. Input shape của model sẽ thay đổi tương ứng.

**Q: Làm sao tái lặp kết quả?**

A: Dùng cùng `--seed` và cùng bộ data. Kết quả có thể chênh lệch nhỏ do thứ tự file và floating point trên các máy khác nhau.

---

## Lịch sử thực hiện trong dự án này

| Bước | Dữ liệu | Kết quả |
|---|---|---|
| Demo run (kiểm thử pipeline) | 400 bonafide tổng hợp + 400 spoof TTS | Accuracy 1.0 (expected, demo only) |
| **Cần thực hiện** | Kaggle FOR dataset (~80k files) | Kỳ vọng Accuracy ≥ 0.88, F1 ≥ 0.87 |

File model hiện tại trong `app/src/main/assets/models/voice_spoof_detector.tflite` là **demo model** — cần thay thế bằng model train từ Kaggle dataset.
