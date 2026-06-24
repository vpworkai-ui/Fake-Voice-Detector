# Kế hoạch cải thiện training theo thuộc tính âm thanh

Tài liệu này ghi lại các thay đổi được áp dụng sau khi đọc luận văn `docs/thesis/LuanVan_NguyenKimNgan.docx` và kết quả test ngoài nguồn tiếng Việt.

## Vấn đề hiện tại

Ba model deep learning đạt gần 100% trên test nội bộ, nhưng giảm mạnh khi đánh giá trên dữ liệu tiếng Việt khác nguồn. Điều này cho thấy model đang học tốt ranh giới giữa VIVOS và `mc_thu_hue`, nhưng chưa đủ bền với khác biệt về thiết bị thu, biên độ, nhiễu nền, cách tổng hợp TTS và phân phối giọng.

Vì vậy, chỉ nhìn accuracy của split nội bộ là chưa đủ để kết luận model tốt cho nghiệm thu. Cần báo cáo song song:

- Internal test: cùng nguồn với training, dùng để kiểm tra model có học được bài toán không.
- External Vietnamese test: khác nguồn, dùng để đo khả năng tổng quát.
- Threshold analysis: so sánh ngưỡng cố định `0.5` với ngưỡng tối ưu trên tập đánh giá.

## Ý lấy từ luận văn

Luận văn dùng 8 đặc trưng âm thanh thủ công, rẻ cho Android:

| Feature | Ý nghĩa |
|---|---|
| `rms` | Năng lượng hiệu dụng |
| `mean_abs` | Biên độ tuyệt đối trung bình |
| `zcr` | Tỷ lệ đổi dấu, liên quan thành phần tần số cao |
| `peak` | Biên độ đỉnh |
| `crest_factor` | Tỷ lệ peak/RMS, phản ánh độ nhọn của tín hiệu |
| `clipping_ratio` | Tỷ lệ mẫu bị clipping/gần bão hòa |
| `dynamic_range` | Dải động của tín hiệu |
| `active_duration_sec` | Thời lượng vùng có tín hiệu sau chuẩn hóa |

Các feature này không đủ mạnh để thay thế deep model khi gặp TTS hiện đại, nhưng hữu ích làm nhánh phụ vì chúng cung cấp thông tin năng lượng/dải động/méo tín hiệu mà spectrogram hoặc raw waveform có thể học lệch theo nguồn.

## Thay đổi đã áp dụng vào code

File chính: `ml/benchmark_android_models.py`

- Thêm `augment_audio()` cho train-time augmentation:
  - random gain `-6dB` đến `+6dB`
  - random time shift tối đa 10% độ dài input
  - random Gaussian noise theo SNR 12-30dB
- Thêm `acoustic_features()` để trích xuất 8 feature theo hướng luận văn.
- Thêm nhánh phụ `feature_input` cho cả 3 model khi bật `--acoustic-features`.
- Giữ tương thích model cũ: nếu không bật flag mới, kiến trúc và input vẫn như trước.
- Lưu cấu hình `augment`, `acoustic_features`, và thứ tự feature vào `summary.json`.

File đánh giá: `ml/evaluate_external_models.py`

- Tự nhận biết model có dùng nhánh acoustic feature hay không từ `summary.json`.
- Thêm `--models` để đánh giá một hoặc nhiều model tùy chọn.
- Báo thêm `best_accuracy_threshold` và `best_external_acc`, không chỉ accuracy tại threshold `0.5`.

## Lệnh train lại 3 model theo hướng mới

```bash
cd /Users/phucit/Desktop/Work/Apps/Flutter/Projects/fake_voice_detector
source ml/.venv/bin/activate

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

Với cấu hình trên, split vẫn dùng đủ 24.840 file:

| Split | Số file |
|---|---:|
| Train | 20.556 |
| Validation | 2.284 |
| Test | 2.000 |
| Tổng | 24.840 |

## Lệnh đánh giá ngoài nguồn

```bash
python ml/evaluate_external_models.py \
  --models-dir ml/artifacts/android_model_benchmark_acoustic_augmented \
  --external-root data/external_vietnamese_test \
  --output-dir ml/artifacts/external_evaluation_vietnamese_acoustic_augmented \
  --limit-per-class 1000 \
  --batch-size 32
```

Output cần đưa vào báo cáo:

- `ml/artifacts/android_model_benchmark_acoustic_augmented/summary.json`
- `ml/artifacts/external_evaluation_vietnamese_acoustic_augmented/REPORT.md`
- `ml/artifacts/external_evaluation_vietnamese_acoustic_augmented/comparison.csv`

## Cách so sánh trước và sau bổ sung

So sánh hai bộ kết quả:

| Bộ kết quả | Thư mục |
|---|---|
| Trước cải thiện | `ml/artifacts/android_model_benchmark_teacher_split` |
| Sau cải thiện | `ml/artifacts/android_model_benchmark_acoustic_augmented` |

Các chỉ số ưu tiên:

- External accuracy tại threshold `0.5`
- Best external accuracy sau calibration threshold
- External AUC
- External EER
- Số `FP` và `FN`, đặc biệt `FN` vì bỏ sót spoof là lỗi nguy hiểm trong bài toán này
- Kích thước TFLite và số tham số để cân bằng với Android

## Kỳ vọng thực tế

Augmentation và nhánh acoustic feature có thể cải thiện khả năng tổng quát mà không cần tăng số file, nhưng không nên kỳ vọng từ khoảng 50% lên 95-99% nếu external spoof đến từ TTS khác hẳn nguồn train. Để nghiệm thu chắc hơn, hướng đúng là:

1. Giữ split nội bộ để báo cáo tái lập.
2. Dùng external Vietnamese test để chứng minh khách quan.
3. Train bản cải thiện với augmentation + acoustic feature.
4. Nếu external vẫn thấp, bổ sung 1-2K spoof/bonafide khác nguồn như thầy gợi ý và train lại.
