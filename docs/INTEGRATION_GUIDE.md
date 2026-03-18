# Integration Guide (Production)

Tài liệu này mô tả các phần đã tích hợp trong app và các phần cần bạn nối với hạ tầng thật.

## 1) Build-time config bắt buộc

App đọc biến cấu hình theo thứ tự:
1. `gradle.properties` (project)
2. environment variables
3. fallback mặc định

Biến hỗ trợ:

- `ASV_ENDPOINT`: endpoint tính ASV score
- `TELEMETRY_ENDPOINT`: endpoint nhận telemetry events
- `ASV_API_KEY`: API key cho ASV backend
- `TELEMETRY_API_KEY`: API key cho telemetry backend

Ví dụ trong `gradle.properties`:

```properties
ASV_ENDPOINT=https://your-domain.com/api/asv/score
TELEMETRY_ENDPOINT=https://your-domain.com/api/telemetry/events
ASV_API_KEY=replace_with_real_key
TELEMETRY_API_KEY=replace_with_real_key
```

## 2) Model anti-spoof production

Đặt model tại:

`app/src/main/assets/models/voice_spoof_detector.tflite`

Yêu cầu đầu vào/đầu ra: xem `app/src/main/assets/models/README.md`.

Lưu ý release mode:
- Không có model hoặc inference lỗi => app fail phiên xác thực (không fallback heuristic).

## 3) ASV backend contract

Endpoint: `POST $ASV_ENDPOINT`

Request:

```json
{
  "spoofProbability": 0.21,
  "recordingDurationSec": 2.43,
  "sessionTimestampMs": 1710000000000
}
```

Response:

```json
{
  "asvScore": 0.84,
  "source": "remote"
}
```

Headers app gửi (nếu có API key):
- `Authorization: Bearer <ASV_API_KEY>`
- `X-Api-Key: <ASV_API_KEY>`

## 4) Telemetry backend contract

Endpoint: `POST $TELEMETRY_ENDPOINT`

Payload mỗi event (JSON line):

```json
{
  "timestampMs": 1710000000000,
  "spoofProbability": 0.2,
  "asvScore": 0.88,
  "decision": "ALLOW",
  "reason": "ASV accepted and spoof risk low",
  "asvSource": "remote",
  "asvLatencyMs": 120,
  "modelName": "tflite-voice-spoof-detector",
  "recordingDurationSec": 2.4
}
```

Headers app gửi (nếu có API key):
- `Authorization: Bearer <TELEMETRY_API_KEY>`
- `X-Api-Key: <TELEMETRY_API_KEY>`

Store-and-forward:
- Log đầy đủ: `<app_files_dir>/telemetry/voice_auth_events.jsonl`
- Queue pending retry: `<app_files_dir>/telemetry/voice_auth_pending.jsonl`

## 5) Các phần app đã khóa trong release

- Bắt buộc remote ASV.
- Bắt buộc endpoint ASV không phải placeholder (`example.com` / `localhost`).
- Không manual score fallback.
- Không heuristic anti-spoof fallback.

## 6) Những phần cần bạn triển khai ngoài app

1. Backend ASV model service thật (suy luận speaker verification score).
2. Backend telemetry ingestion + storage + dashboard/alerting.
3. Quản lý secrets/API keys an toàn (CI/CD secret manager).
4. Dataset eval pipeline (EER/t-DCF) cho model anti-spoof trước khi phát hành.
5. Chính sách step-up auth ở backend khi decision = `REVIEW`.

## 7) UAT checklist trước go-live

1. Test 50 mẫu bonafide + 50 mẫu spoof/replay/TTS.
2. Xác nhận tỉ lệ lỗi theo KPI (FAR/FRR nội bộ).
3. Verify timeout/retry khi backend gián đoạn.
4. Verify pending telemetry được flush lại khi mạng hồi phục.
5. Verify release build fail-safe khi thiếu model hoặc endpoint placeholder.
