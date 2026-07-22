# Voice Spoof Model Placement

App Android hiện chỉ bundle model deploy mặc định tại:

`app/src/main/assets/models/voice_spoof_detector.tflite`

Các model đối chiếu hoặc artifact huấn luyện khác nên được lưu ở `ml/artifacts/` thay vì đặt thêm trong `app/src/main/assets/models/`.

Thư mục assets của ứng dụng chỉ nên chứa model đang được ứng dụng nạp ở runtime. Các số liệu huấn luyện, benchmark hoặc kết quả đánh giá cần được giữ trong tài liệu/kho artifact riêng, không nên xem là dữ liệu runtime của app.

Model deploy hien tai cua app khop voi artifact `cross_scale_attention_lite` trong repo.

Yeu cau dau vao hien tai cua app:
- single-input: `[1, N]` voi `N >= 8` de tuong thich voi cac model doi chieu
- dual-input: spectrogram + acoustic features; day la nhanh model deploy mac dinh hien tai trong APK

Thứ tự 8 đặc trưng acoustic nền:
- `rms, meanAbs, zcr, peak, crestFactor, clippingRatio, dynamicRange, durationSec`

Ghi chú:
- Trong runtime Android hiện tại, đặc trưng cuối cùng là `durationSec` = tổng thời lượng đoạn audio đầu vào sau khi chuẩn hóa/padding.
- Một số tài liệu hoặc script nghiên cứu cũ còn gọi đặc trưng này là `active_duration_sec`; tên đó không phản ánh chính xác hành vi runtime đang deploy trong APK.

Dau ra ho tro:
- `[1, 1]`: spoof probability hoac logit
- `[1, 2]`: `[bonafide, spoof]` duoi dang probability hoac logit

App khong con su dung heuristic fallback. Neu model khong tai duoc hoac suy luan that bai, ung dung phai bao loi that de tranh sinh ra ket qua gia.
