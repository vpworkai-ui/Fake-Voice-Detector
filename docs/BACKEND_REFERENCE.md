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

## Curl test nhanh

ASV:

```bash
curl -sS -X POST http://127.0.0.1:8080/api/asv/score \
  -H 'Content-Type: application/json' \
  -H 'X-Api-Key: replace_with_asv_key' \
  -d '{"spoofProbability":0.2,"recordingDurationSec":2.4,"sessionTimestampMs":1710000000000}'
```

Telemetry:

```bash
curl -sS -X POST http://127.0.0.1:8080/api/telemetry/events \
  -H 'Content-Type: application/json' \
  -H 'X-Api-Key: replace_with_telemetry_key' \
  -d '{"timestampMs":1710000000000,"spoofProbability":0.2,"asvScore":0.88,"decision":"ALLOW","reason":"ok","asvSource":"remote","asvLatencyMs":100,"modelName":"tflite-voice-spoof-detector","recordingDurationSec":2.4}'
```
