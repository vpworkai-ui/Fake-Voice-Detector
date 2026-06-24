# Ket qua training lai 3 model voi augmentation va acoustic features

Ngay thuc hien: 19-05-2026

## Cau hinh chung

- Dataset train/validation/test noi bo: `data/dataset_samples`
- Tong so file dung trong split noi bo: 24,840
- Bonafide: 12,420 file
- Spoof: 12,420 file
- Split da dung:
  - Train: 20,556 file
  - Validation: 2,284 file
  - Test noi bo: 2,000 file
- External Vietnamese test: `data/external_vietnamese_test`
  - Bonafide ngoai nguon train: 1,000 file
  - Spoof ngoai nguon train: 1,000 file
- Sample rate: 16 kHz
- Do dai toi da moi mau: 4 giay
- Bo sung khi training:
  - Random gain
  - Time shift
  - Gaussian noise
  - 8 acoustic features: rms, mean_abs, zcr, peak, crest_factor, clipping_ratio, dynamic_range, active_duration_sec

## Ket qua noi bo sau khi train lai

| Model | So tham so | Epoch chay | Internal test accuracy | Internal AUC | TFLite size |
|---|---:|---:|---:|---:|---:|
| Cross-Scale Attention Lite | 151,610 | 4 | 99.75% | 0.999998 | 183 KB |
| AASIST Lite | 76,705 | 4 | 99.95% | 0.999996 | 144 KB |
| CBAM ResNet Lite | 350,563 | 8 | 99.75% | 0.999999 | 432 KB |

Nhan xet: ca 3 model deu dat accuracy noi bo rat cao. Tuy nhien, day chua phai bang chung du manh de ket luan model tong quat tot, vi test noi bo van cung mien du lieu voi train.

## Ket qua test ngoai nguon tieng Viet voi threshold 0.5

| Model | External acc @0.5 | Precision | Recall | F1 | External AUC | EER | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cross-Scale Attention Lite | 51.25% | 54.15% | 16.30% | 25.06% | 0.705529 | 35.40% | 138 | 837 |
| AASIST Lite | 49.80% | 30.00% | 0.30% | 0.59% | 0.608109 | 42.85% | 7 | 997 |
| CBAM ResNet Lite | 49.90% | 25.00% | 0.10% | 0.20% | 0.723069 | 33.50% | 3 | 999 |

Nhan xet: khi doi sang du lieu ngoai nguon, ca 3 model deu giam manh neu giu threshold mac dinh 0.5. Cross-Scale co accuracy cao nhat trong 3 model o threshold 0.5, nhung recall lop spoof chi dat 16.30%. AASIST va CBAM gan nhu khong phat hien duoc file spoof ngoai nguon tai threshold nay. Dieu nay cho thay model chua tong quat tot tren nguon du lieu moi.

## So sanh truoc va sau bo sung

| Model | External acc cu @0.5 | External acc moi @0.5 | AUC cu | AUC moi | EER cu | EER moi |
|---|---:|---:|---:|---:|---:|---:|
| Cross-Scale Attention Lite | 52.90% | 51.25% | 0.790048 | 0.705529 | 27.90% | 35.40% |
| AASIST Lite | 48.35% | 49.80% | 0.549073 | 0.608109 | 48.35% | 42.85% |
| CBAM ResNet Lite | 48.40% | 49.90% | 0.642529 | 0.723069 | 40.15% | 33.50% |

## Ket luan tam thoi

- Neu chi xet test noi bo, ca 3 model deu qua cao va gan nhu khong phan biet duoc chat luong that.
- Khi test ngoai nguon voi threshold 0.5, Cross-Scale co accuracy cao nhat trong 3 model: 51.25%.
- CBAM co AUC cao nhat va EER thap nhat, nhung accuracy tai threshold 0.5 van thap va model lon hon nhieu.
- AASIST Lite nho nhat, phu hop Android nhat ve dung luong, nhung do tong quat ngoai nguon thap hon 2 model con lai.
- Huong nen bao cao voi thay: khong chi dua vao internal accuracy, ma can them external Vietnamese test. Ket qua hien tai cho thay van con domain shift lon giua nguon train va nguon test ngoai.

## File ket qua

- Training summary: `ml/artifacts/android_model_benchmark_acoustic_augmented/summary.json`
- External report: `ml/artifacts/external_evaluation_vietnamese_acoustic_augmented/REPORT.md`
- External comparison CSV: `ml/artifacts/external_evaluation_vietnamese_acoustic_augmented/comparison.csv`
- TFLite Cross-Scale: `ml/artifacts/android_model_benchmark_acoustic_augmented/cross_scale_attention_lite/model_dynamic_quant.tflite`
- TFLite AASIST: `ml/artifacts/android_model_benchmark_acoustic_augmented/aasist_lite/model_dynamic_quant.tflite`
- TFLite CBAM: `ml/artifacts/android_model_benchmark_acoustic_augmented/cbam_resnet_lite/model_dynamic_quant.tflite`
