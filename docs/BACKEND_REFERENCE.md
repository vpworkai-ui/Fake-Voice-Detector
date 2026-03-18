# Backend Reference (Minimal)

## ASV endpoint

- Method: `POST`
- Path: `/api/asv/score`
- Request JSON:
  - `spoofProbability` (float)
  - `recordingDurationSec` (float)
  - `sessionTimestampMs` (long)
- Response JSON:
  - `asvScore` (float 0..1)
  - `source` (string, optional)

## Telemetry endpoint

- Method: `POST`
- Path: `/api/telemetry/events`
- Request JSON: event object từ app
- Response: HTTP 2xx nếu nhận thành công

## Khuyến nghị backend

1. Giới hạn rate + auth bằng API key/JWT.
2. Log request id để trace end-to-end.
3. Timeout <= 2s cho ASV endpoint.
4. Trả JSON lỗi có thông điệp ngắn gọn.
