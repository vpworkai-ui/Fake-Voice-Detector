# Training Pipeline (from in-app captured files)

Pipeline này train model anti-spoof từ dữ liệu bạn thu trong app (`bonafide/spoof`) rồi export `.tflite` để dùng lại trong Android app.

## 1) Export dữ liệu từ app (debug)

```bash
cd /Users/phucit/Desktop/Work/KMP/Repos/fake_voice_detector
./scripts/export_dataset_from_device.sh com.vpsaker.fake_voice_detector ./data
```

Sau lệnh này bạn sẽ có:

- `./data/dataset_samples/bonafide/*.wav`
- `./data/dataset_samples/spoof/*.wav`

## 2) Cài môi trường training

```bash
cd /Users/phucit/Desktop/Work/KMP/Repos/fake_voice_detector/ml
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Train model

```bash
python train_spoof_model.py \
  --dataset-root ../data/dataset_samples \
  --output-dir ./artifacts \
  --epochs 30
```

Output:

- `artifacts/voice_spoof_detector.keras`
- `artifacts/voice_spoof_detector.tflite`
- `artifacts/feature_stats.npy`
- `artifacts/report.json`

## 4) Đưa model vào app

Copy file `.tflite` sang:

`/Users/phucit/Desktop/Work/KMP/Repos/fake_voice_detector/app/src/main/assets/models/voice_spoof_detector.tflite`

Build lại app:

```bash
cd /Users/phucit/Desktop/Work/KMP/Repos/fake_voice_detector
./gradlew assembleDebug
```

## Ghi chú

- Script train dùng đúng feature order như app Android.
- Nên có tối thiểu 100 mẫu mỗi lớp cho kết quả ổn định hơn.
- Khi training nghiêm túc, nên tách dữ liệu theo speaker/session để tránh leakage.
