# 3.3. Đánh giá hiệu năng hệ thống

Mục tiêu phần này là đánh giá toàn diện ứng dụng phát hiện giả mạo giọng nói trên Android theo cả góc nhìn mô hình và góc nhìn vận hành thực tế.

## 3.3.1. Độ chính xác mô hình

### Chỉ số đánh giá

- **Accuracy**: tỷ lệ dự đoán đúng trên toàn bộ mẫu.
- **Precision (lớp Spoof)**: trong các mẫu hệ thống dự đoán spoof, tỷ lệ đúng thực sự là spoof.
- **Recall (lớp Spoof)**: trong các mẫu spoof thực tế, hệ thống phát hiện được bao nhiêu.
- **F1-score**: trung bình điều hòa giữa Precision và Recall, phản ánh cân bằng giữa phát hiện đúng và cảnh báo sai.

### Quy trình đo

1. Chuẩn bị tập kiểm thử gồm ít nhất:
- 50 mẫu `bonafide` (giọng thật).
- 50 mẫu `spoof` (TTS/replay/voice conversion nếu có).
2. Chạy toàn bộ mẫu qua ứng dụng với cùng cấu hình threshold.
3. Lập confusion matrix (`TP`, `FP`, `TN`, `FN`).
4. Tính Accuracy, Precision, Recall, F1-score theo công thức chuẩn.

### Bảng kết quả dự kiến (mẫu)

| Chỉ số | Giá trị dự kiến |
|---|---:|
| Accuracy | 0.85 - 0.93 |
| Precision (Spoof) | 0.84 - 0.92 |
| Recall (Spoof) | 0.82 - 0.91 |
| F1-score (Spoof) | 0.83 - 0.91 |

Ghi chú: khoảng giá trị phụ thuộc chất lượng model `.tflite`, dữ liệu thực nghiệm và ngưỡng quyết định.

## 3.3.2. Thời gian phản hồi (Latency)

### Thành phần độ trễ

- `T_record`: thời gian người dùng ghi âm.
- `T_feature`: thời gian trích xuất đặc trưng.
- `T_spoof`: thời gian suy luận anti-spoof on-device.
- `T_asv_api`: thời gian gọi backend ASV.
- `T_fusion`: thời gian hợp nhất quyết định.

### Chỉ số báo cáo

- **Latency trung bình** (mean)
- **Latency P95**
- **Latency max**

### Bảng kết quả dự kiến (mẫu)

| Thành phần | Giá trị dự kiến |
|---|---:|
| `T_feature + T_spoof` | 80 - 220 ms |
| `T_asv_api` (LAN/WiFi) | 120 - 450 ms |
| Tổng sau khi bấm Analyze | 250 - 800 ms |
| P95 tổng | < 1200 ms |

## 3.3.3. Mức sử dụng CPU, RAM và pin

### Cách đo

- Dùng Android Studio Profiler (CPU, Memory, Energy) trong 3 kịch bản:
1. Idle (mở app, chưa ghi âm)
2. Recording
3. Analyze (on-device + API)

### Chỉ số báo cáo

- CPU trung bình và đỉnh (% theo process app)
- RAM trung bình và đỉnh (MB)
- Pin tiêu hao theo phiên kiểm thử (ước lượng mAh hoặc % pin/30 phút test liên tục)

### Bảng kết quả dự kiến (mẫu)

| Trạng thái | CPU trung bình | RAM trung bình | Pin tiêu hao |
|---|---:|---:|---:|
| Idle | 2% - 6% | 110 - 170 MB | rất thấp |
| Recording | 6% - 18% | 130 - 210 MB | thấp-trung bình |
| Analyze | 12% - 35% | 150 - 260 MB | trung bình |

## 3.3.4. So sánh hiệu năng giữa môi trường huấn luyện và môi trường thực tế

### Môi trường huấn luyện

- Dữ liệu sạch hơn, cân bằng hơn.
- Thiết bị tính toán mạnh (GPU/CPU server).
- Điều kiện ít nhiễu.

### Môi trường thực tế

- Nhiễu nền, micro khác nhau, khoảng cách nói khác nhau.
- Thiết bị Android đa dạng (CPU/RAM khác nhau).
- Kết nối mạng biến động làm tăng `T_asv_api`.

### Nội dung so sánh đề xuất

1. So sánh Accuracy/F1 giữa tập validation và tập thu thực tế.
2. So sánh latency giữa thiết bị tầm trung và cao cấp.
3. So sánh tỷ lệ `ALLOW/REVIEW/BLOCK` khi cùng một người dùng ở môi trường yên tĩnh và môi trường nhiễu.

### Kết luận dự kiến

- Hiệu năng thực tế thường giảm nhẹ so với môi trường huấn luyện.
- Cần hiệu chỉnh threshold theo dữ liệu thực tế để cân bằng FAR/FRR.
- Cần theo dõi telemetry liên tục để phát hiện drift và cập nhật mô hình/ngưỡng định kỳ.

## 3.3.5. Tiêu chí đạt cho đồ án

Đề xuất tiêu chí nghiệm thu:

- F1-score lớp spoof >= 0.85
- Recall lớp spoof >= 0.85
- Latency tổng trung bình < 1.0 giây
- P95 latency < 1.5 giây
- Ứng dụng chạy ổn định trên ít nhất 2 dòng máy Android khác nhau

