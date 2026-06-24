# Ke hoach training va so sanh cac model audio deepfake detection

Tai lieu nay dung de chuyen project tu model demo hien tai sang mot pipeline nghiem thu co co so hoc thuat ro rang. Muc tieu la train nhieu model tren cung tap du lieu hien co, danh gia bang cung protocol, sau do chon model phu hop nhat de dua vao Android/TFLite.

## 1. Ket luan nhanh

Model hien tai trong project la baseline DNN 8-feature:

```text
Input: 8 handcrafted features
Dense(64, ReLU)
Dropout(0.2)
Dense(32, ReLU)
Dense(1)
```

Model nay chi co khoang 2.7k tham so, phu hop lam baseline on-device, nhung khong du thuyet phuc neu bao cao la model chinh dat do chinh xac cao. Ke hoach moi se so sanh baseline nay voi cac huong manh hon:

1. Baseline hien tai: DNN 8-feature.
2. LFCC/MFCC + LCNN/CNN nho.
3. RawNet2 anti-spoofing.
4. AASIST / AASIST-L.
5. wav2vec2-AASIST hoac SSL-AASIST.
6. Resolution-aware cross-scale model theo paper thay gui.

## 2. Paper va model tham khao

| Nhom model | Nam | Nguon | Ly do chon |
|---|---:|---|---|
| DNN 8-feature baseline | 2025-2026 project | `ml/train_spoof_model.py` | Nhe, dang co san, lam moc so sanh |
| RawNet2 anti-spoofing | 2021 | https://www.eurecom.org/en/publication/6395 | End-to-end tren raw waveform, co open-source reproducible |
| AASIST / AASIST-L | 2022 | https://www.eurecom.org/en/publication/6696 | Model anti-spoofing rat noi tieng; AASIST-L chi khoang 85k tham so |
| wav2vec2 anti-spoofing | 2022 | https://huggingface.co/papers/2202.12233 | SSL speech representation, ket qua manh tren ASVspoof 2021 LA/DF |
| Resolution-aware cross-scale | 2026 | https://arxiv.org/abs/2601.06560 | Paper thay gui; lightweight 159k tham so, multi-resolution spectrogram + attention |
| Scalable AASIST | 2025 | https://huggingface.co/papers/2507.11777 | Huong nang cap AASIST bang wav2vec2/multi-head attention |

Ghi chu: cac model SSL nhu wav2vec2/WavLM thuong manh nhung nang hon, kho dua truc tiep vao Android. Chung nen dung lam upper-bound hoac backend/reference model. Cac model nhe nhu AASIST-L, LFCC-CNN va resolution-aware 159k tham so phu hop hon cho TFLite on-device.

## 3. Data hien co va cach chuan hoa

Project hien tai dang huong toi cac nguon data:

| Data | Vai tro | Vi tri/ghi chu |
|---|---|---|
| VIVOS | bonafide tieng Viet | `data/dataset_samples/bonafide` sau khi prepare |
| mc_thu_hue_fix_char | spoof/TTS tieng Viet | `data/dataset_samples/spoof` sau khi prepare |
| Data tu app Android | bonafide/spoof tu thiet bi thuc | export bang `scripts/export_dataset_from_device.sh` |
| Kaggle FoR | real/fake reference dataset | khuyen nghi them de test cross-domain |

Tat ca model phai dung cung mot manifest de tranh sai lech split:

```text
data/manifests/train.csv
data/manifests/val.csv
data/manifests/test.csv
data/manifests/cross_test.csv
```

Format moi dong:

```csv
path,label,speaker_id,source,duration_sec
/abs/path/file.wav,bonafide,spk001,VIVOS,3.21
/abs/path/file.wav,spoof,tts001,mc_thu_hue,2.87
```

Nguyen tac split:

1. Speaker-disjoint neu co `speaker_id`.
2. Khong de cung speaker hoac cung file goc xuat hien o ca train va test.
3. Test rieng cross-domain: train tren VIVOS + mc_thu_hue, test tren FoR hoac data tu app.
4. Bao cao ca within-domain va cross-domain, khong chi bao cao random split.

## 4. Metric so sanh

Moi model can xuat cung bo metric:

| Metric | Ly do |
|---|---|
| Accuracy | De giai thich de hieu trong do an |
| Precision, Recall, F1 | Can bang loi bao nham fake/real |
| ROC-AUC | Do phan tach tong quat |
| EER | Metric chuan cho anti-spoofing |
| minDCF neu co | Gan voi ASVspoof |
| Params | Chung minh model nhe/nang |
| FLOPs/MACs | Phu hop trien khai mobile |
| Inference latency | Do tren may tinh va Android |
| TFLite size | Quan trong voi app Android |

Ket qua chinh nen uu tien EER, F1, AUC va cross-domain EER.

## 5. Cach chay model baseline hien tai

Baseline nay da co script trong repo.

### Prepare data

```bash
python ml/prepare_dataset.py \
  --mode custom \
  --bonafide-src data/device_dataset/bonafide \
  --spoof-src data/device_dataset/spoof \
  --output data/dataset_samples
```

Hoac voi Kaggle FoR:

```bash
python ml/prepare_dataset.py \
  --mode kaggle \
  --source ~/Downloads/for-norm \
  --output data/dataset_samples
```

### Train baseline

```bash
python ml/train_spoof_model.py \
  --dataset-root data/dataset_samples \
  --output-dir ml/artifacts/baseline_dnn8 \
  --epochs 30 \
  --batch-size 32 \
  --seed 42
```

### Export vao Android

```bash
cp ml/artifacts/baseline_dnn8/voice_spoof_detector.tflite \
  app/src/main/assets/models/voice_spoof_detector.tflite
```

Can sua diem yeu hien tai: Android dang dua raw feature vao model, trong khi Python training co standardize feature. Neu tiep tuc baseline, can dua `feature_stats.npy` vao Android hoac nhung normalization vao TFLite.

## 6. Model 1 - LFCC/MFCC + CNN/LCNN nho

Muc tieu: model vua suc, de train, de export TFLite, co co so speech anti-spoofing tot hon 8 handcrafted features.

Input de xuat:

```text
LFCC hoac MFCC: [time, freq]
CNN/LCNN nho: conv -> pooling -> conv -> pooling -> dense
```

Lenh train de xuat sau khi them script:

```bash
python ml/train_lfcc_cnn.py \
  --train-manifest data/manifests/train.csv \
  --val-manifest data/manifests/val.csv \
  --test-manifest data/manifests/test.csv \
  --feature lfcc \
  --sample-rate 16000 \
  --max-duration-sec 4 \
  --output-dir ml/artifacts/lfcc_cnn \
  --epochs 50 \
  --batch-size 32 \
  --seed 42
```

Danh gia:

```bash
python ml/evaluate_model.py \
  --model-dir ml/artifacts/lfcc_cnn \
  --test-manifest data/manifests/test.csv \
  --output ml/artifacts/lfcc_cnn/eval_test.json
```

Uu diem:

- Nhe, de TFLite.
- Giai thich duoc voi giao vien.
- Hop ly lam model chinh neu thoi gian co han.

Nhuoc diem:

- Kem hon SSL model khi gap domain moi.

## 7. Model 2 - RawNet2 anti-spoofing

Muc tieu: model end-to-end tu raw waveform, lam moc so sanh voi CNN spectrogram.

Nguon tham khao:

- Paper: https://www.eurecom.org/en/publication/6395

Input:

```text
Raw waveform 16kHz, fixed length 4s hoac 6s
```

Lenh train de xuat sau khi them adapter:

```bash
python ml/train_rawnet2.py \
  --train-manifest data/manifests/train.csv \
  --val-manifest data/manifests/val.csv \
  --test-manifest data/manifests/test.csv \
  --sample-rate 16000 \
  --max-duration-sec 4 \
  --output-dir ml/artifacts/rawnet2 \
  --epochs 50 \
  --batch-size 16 \
  --seed 42
```

Danh gia:

```bash
python ml/evaluate_model.py \
  --model-dir ml/artifacts/rawnet2 \
  --test-manifest data/manifests/test.csv \
  --output ml/artifacts/rawnet2/eval_test.json
```

Uu diem:

- Khong phu thuoc feature thu cong.
- Co paper anti-spoofing ro.

Nhuoc diem:

- Nang hon LFCC-CNN.
- Export TFLite co the kho hon tuy layer.

## 8. Model 3 - AASIST / AASIST-L

Muc tieu: ung vien chinh de thuyet phuc ve mat hoc thuat. AASIST la mot trong cac model anti-spoofing duoc trich dan nhieu; AASIST-L nhe hon va phu hop mobile hon.

Nguon tham khao:

- Paper: https://www.eurecom.org/en/publication/6696

Input:

```text
Raw waveform hoac representation theo official implementation
```

Lenh train de xuat:

```bash
python ml/train_aasist.py \
  --train-manifest data/manifests/train.csv \
  --val-manifest data/manifests/val.csv \
  --test-manifest data/manifests/test.csv \
  --variant aasist_l \
  --sample-rate 16000 \
  --max-duration-sec 4 \
  --output-dir ml/artifacts/aasist_l \
  --epochs 50 \
  --batch-size 16 \
  --seed 42
```

Danh gia:

```bash
python ml/evaluate_model.py \
  --model-dir ml/artifacts/aasist_l \
  --test-manifest data/manifests/test.csv \
  --output ml/artifacts/aasist_l/eval_test.json
```

Uu diem:

- Rat hop voi bai toan voice spoofing.
- Co ban lightweight khoang 85k tham so theo paper.
- Thuyet phuc hon model 2.7k tham so hien tai.

Nhuoc diem:

- Can thoi gian tich hop official architecture.
- Can test ky TFLite compatibility.

## 9. Model 4 - wav2vec2-AASIST / SSL-AASIST

Muc tieu: upper-bound model de so sanh do manh, khong nhat thiet dua truc tiep vao Android.

Nguon tham khao:

- Paper: https://huggingface.co/papers/2202.12233
- Scalable AASIST 2025: https://huggingface.co/papers/2507.11777

Input:

```text
Raw waveform -> pretrained wav2vec2 frontend -> anti-spoofing classifier/AASIST backend
```

Lenh train de xuat:

```bash
python ml/train_ssl_aasist.py \
  --train-manifest data/manifests/train.csv \
  --val-manifest data/manifests/val.csv \
  --test-manifest data/manifests/test.csv \
  --ssl-model facebook/wav2vec2-base \
  --freeze-frontend true \
  --sample-rate 16000 \
  --max-duration-sec 4 \
  --output-dir ml/artifacts/ssl_aasist \
  --epochs 20 \
  --batch-size 4 \
  --seed 42
```

Danh gia:

```bash
python ml/evaluate_model.py \
  --model-dir ml/artifacts/ssl_aasist \
  --test-manifest data/manifests/test.csv \
  --output ml/artifacts/ssl_aasist/eval_test.json
```

Uu diem:

- Thuong manh hon model nhe trong dieu kien data phuc tap.
- Tot de chung minh baseline hien tai yeu.

Nhuoc diem:

- Nang, can GPU.
- Kho dua on-device neu khong quantize/prune rat ky.
- Neu data it, fine-tune de overfit.

## 10. Model 5 - Resolution-aware cross-scale attention theo paper 2026

Muc tieu: huong nang cap gan nhat voi link thay gui, giu tinh lightweight nhung co kien truc hien dai hon.

Nguon:

- Paper: https://arxiv.org/abs/2601.06560

Y tuong implementation cho project:

```text
Audio 16kHz
  -> log-mel spectrogram resolution 1: window 25ms, hop 10ms
  -> log-mel spectrogram resolution 2: window 50ms, hop 20ms
  -> log-mel spectrogram resolution 3: window 100ms, hop 40ms
  -> CNN encoder rieng tung resolution
  -> cross-scale attention
  -> consistency loss giua cac scale
  -> binary classifier
```

Lenh train de xuat:

```bash
python ml/train_cross_scale_attention.py \
  --train-manifest data/manifests/train.csv \
  --val-manifest data/manifests/val.csv \
  --test-manifest data/manifests/test.csv \
  --sample-rate 16000 \
  --max-duration-sec 4 \
  --mel-bins 64 \
  --output-dir ml/artifacts/cross_scale_attention \
  --epochs 50 \
  --batch-size 16 \
  --consistency-weight 0.2 \
  --seed 42
```

Danh gia:

```bash
python ml/evaluate_model.py \
  --model-dir ml/artifacts/cross_scale_attention \
  --test-manifest data/manifests/test.csv \
  --output ml/artifacts/cross_scale_attention/eval_test.json
```

Export TFLite:

```bash
python ml/export_tflite.py \
  --model-dir ml/artifacts/cross_scale_attention \
  --output app/src/main/assets/models/voice_spoof_detector.tflite \
  --quantize dynamic
```

Uu diem:

- Gan voi paper thay gui.
- Van co the giu model nhe khoang 100k-300k tham so.
- Giai thich duoc vi sao tot hon DNN 8-feature: hoc dau vet tren nhieu thang do time-frequency.

Nhuoc diem:

- Can tu implement neu khong co official code.
- Can chuan hoa input spectrogram tren Android.

## 11. Bang so sanh ket qua

Sau khi train, dien ket qua vao bang nay. Khong nen dien so doan neu chua train that tren cung split.

| Model | Params | TFLite size | Test Acc | Test F1 | Test AUC | Test EER | Cross EER | Latency Android | Ghi chu |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| DNN 8-feature baseline | ~2.7k | ~12KB | TBD | TBD | TBD | TBD | TBD | TBD | Dang co |
| LFCC-CNN/LCNN | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | De TFLite |
| RawNet2 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | End-to-end waveform |
| AASIST-L | ~85k theo paper | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Ung vien chinh |
| SSL-AASIST | lon | kho mobile | TBD | TBD | TBD | TBD | TBD | TBD | Upper-bound |
| Cross-scale attention 2026 | ~159k theo paper | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Gan link thay gui |

## 12. Thu tu thuc hien de kip do an

### Giai doan 1 - Lam sach benchmark

1. Tao manifest chung `train.csv`, `val.csv`, `test.csv`.
2. Sua baseline DNN 8-feature de normalization khop Python/Android.
3. Chay lai baseline va luu metric that.
4. Tao script evaluate chung tinh Accuracy, F1, AUC, EER.

### Giai doan 2 - Model nhe de dua vao Android

1. Train LFCC-CNN/LCNN.
2. Train AASIST-L.
3. Thu export TFLite cho 2 model nay.
4. Do latency tren emulator/device.

### Giai doan 3 - Model manh de so sanh hoc thuat

1. Train RawNet2.
2. Train SSL-AASIST neu co GPU.
3. Train cross-scale attention theo paper 2026.
4. So sanh within-domain va cross-domain.

### Giai doan 4 - Chon model dua vao app

Tieu chi chon:

1. Cross-domain EER thap hon baseline ro rang.
2. TFLite export duoc.
3. Latency tren Android chap nhan duoc.
4. Model co paper/source ro de bao ve.

De xuat uu tien:

```text
Neu can nhanh: LFCC-CNN/LCNN
Neu can thuyet phuc: AASIST-L
Neu muon bam sat link thay gui: Cross-scale attention lightweight
Neu can upper-bound de so sanh: SSL-AASIST
```

## 13. Cau tra loi co the noi voi thay

Model hien tai la baseline DNN 8-feature, chi khoang 2.7k tham so nen em dong y la chua du manh de lam model chinh. Em se giu no lam baseline, sau do train va so sanh voi cac model anti-spoofing co co so hoc thuat hon nhu AASIST-L, RawNet2, wav2vec2-AASIST va mot model lightweight multi-resolution theo paper thay gui. Tat ca model se duoc danh gia tren cung train/val/test split, co them cross-domain test va bao cao Accuracy, F1, AUC, EER, so tham so, kich thuoc TFLite va latency tren Android.

