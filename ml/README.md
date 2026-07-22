# ML Training Pipeline

Thư mục này chứa toàn bộ pipeline huấn luyện mô hình anti-spoof.

> **Hướng dẫn đầy đủ**: xem [docs/training/README.md](../docs/training/README.md).

## Cấu trúc thư mục

```
ml/
  prepare_dataset.py       ← Chuẩn bị dataset (Kaggle / custom / demo)
  train_spoof_model.py     ← Trích xuất features + train DNN → export .tflite
  generate_charts.py       ← Sinh biểu đồ đánh giá (ROC, AUC, EER, Confusion Matrix)
  generate_thesis_figures.py ← Sinh hình minh hoạ kiến trúc cho luận văn
  requirements.txt         ← Thư viện Python (numpy, scikit-learn, tensorflow)
  artifacts/               ← Output sau khi train (bị .gitignore, không đẩy lên Git)
  charts/                  ← Output biểu đồ (bị .gitignore)
```

## Cài môi trường

```bash
cd /path/to/fake_voice_detector/ml
/opt/homebrew/bin/python3.13 -m venv .venv   # macOS — dùng Python 3.13 từ Homebrew
source .venv/bin/activate
pip install -r requirements.txt
```

## Luồng huấn luyện nhanh

### 1) Chuẩn bị dataset

**Kaggle "The Fake or Real Dataset" (khuyến nghị):**
```bash
python ml/prepare_dataset.py \
  --mode kaggle \
  --source ~/Downloads/for-norm \
  --output data/dataset_samples \
  --limit 2000
```

**Dữ liệu tự thu từ app Android:**
```bash
# Kéo file từ thiết bị trước
./scripts/export_dataset_from_device.sh com.vpsaker.fake_voice_detector ./data

# Chuẩn bị
python ml/prepare_dataset.py \
  --mode custom \
  --bonafide-src data/device_dataset/bonafide \
  --spoof-src    data/device_dataset/spoof \
  --output       data/dataset_samples
```

**Demo (chỉ kiểm thử pipeline, không có giá trị thực tế):**
```bash
python ml/prepare_dataset.py \
  --mode demo \
  --spoof-src resources/mc_thu_hue_fix_char/wavs \
  --output data/dataset_samples
```

### 2) Train model

```bash
python ml/train_spoof_model.py \
  --dataset-root data/dataset_samples \
  --output-dir   ml/artifacts \
  --epochs       30 \
  --batch-size   32 \
  --seed         42
```

Output: `ml/artifacts/voice_spoof_detector.tflite` (cần cho app Android)

### 3) Sinh biểu đồ đánh giá (AUC, EER, ROC…)

```bash
python ml/generate_charts.py
```

Output: `ml/charts/roc_curve.png`, `confusion_matrix.png`, `training_curves.png`, v.v.

### 4) Copy model vào app

```bash
cp ml/artifacts/voice_spoof_detector.tflite \
   app/src/main/assets/models/voice_spoof_detector.tflite
```

## Ghi chú

- Feature order phải khớp giữa Python (`extract_features()`) và Kotlin (`AudioFeatureExtractor.kt`):
  `rms → meanAbs → zcr → peak → crestFactor → clippingRatio → dynamicRange → durationSec`
- Với app Android đang deploy, phần tử thứ 8 hiện được hiểu là `durationSec` của toàn bộ đoạn audio, không phải VAD-based `activeDuration`.
- Một số script nghiên cứu / train lại trong `ml/` vẫn giữ tên lịch sử `active_duration_sec` để tương thích với artifact cũ; khi đối chiếu với runtime Android, ưu tiên đọc theo [app/src/main/assets/models/README.md](../app/src/main/assets/models/README.md).
- `artifacts/` và `charts/` không được đẩy lên Git (xem `.gitignore`)
- Cần tối thiểu ~200 file/lớp; khuyến nghị 1000+ file/lớp cho kết quả tốt
