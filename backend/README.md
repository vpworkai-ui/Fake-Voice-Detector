# Backend (FastAPI)

Backend mẫu cho đồ án để app Android gọi ngay.

## Endpoints

- `GET /health`
- `POST /api/asv/score`
- `POST /api/telemetry/events`

## Chạy local

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./run.sh
```

Server mặc định chạy `http://0.0.0.0:8080`.

## Cấu hình key

Trong `.env`:

```env
ASV_API_KEY=replace_with_asv_key
TELEMETRY_API_KEY=replace_with_telemetry_key
```

Nếu key để trống, endpoint tương ứng sẽ chạy không yêu cầu auth.

## Log file

- `backend/data/asv_requests.jsonl`
- `backend/data/telemetry_events.jsonl`

## Contract

### `POST /api/asv/score`
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
  "source": "backend-baseline-v1"
}
```

### `POST /api/telemetry/events`
Request: JSON event từ app.

Response:

```json
{
  "accepted": true
}
```

## Lưu ý

Backend này là baseline integration cho đồ án. Khi lên production, thay logic `_compute_asv_score` bằng model ASV thật.
