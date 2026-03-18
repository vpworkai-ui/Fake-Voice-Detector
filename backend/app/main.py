from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()


class AsvScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spoofProbability: float = Field(ge=0.0, le=1.0)
    recordingDurationSec: float = Field(ge=0.0, le=30.0)
    sessionTimestampMs: int


class AsvScoreResponse(BaseModel):
    asvScore: float = Field(ge=0.0, le=1.0)
    source: str


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestampMs: int
    spoofProbability: float
    asvScore: float
    decision: str
    reason: str
    asvSource: str
    asvLatencyMs: int
    modelName: str
    recordingDurationSec: float


ASV_API_KEY = os.getenv("ASV_API_KEY", "").strip()
TELEMETRY_API_KEY = os.getenv("TELEMETRY_API_KEY", "").strip()
LOG_DIR = Path(os.getenv("LOG_DIR", "./data")).resolve()
LOG_DIR.mkdir(parents=True, exist_ok=True)

ASV_LOG_FILE = LOG_DIR / "asv_requests.jsonl"
TELEMETRY_LOG_FILE = LOG_DIR / "telemetry_events.jsonl"

write_lock = Lock()

app = FastAPI(title="Fake Voice Detector Backend", version="1.0.0")


def _extract_api_key(authorization: Optional[str], x_api_key: Optional[str]) -> str:
    if x_api_key:
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _assert_auth(expected_key: str, provided_key: str, endpoint_name: str) -> None:
    if not expected_key:
        return
    if provided_key != expected_key:
        raise HTTPException(status_code=401, detail=f"Invalid API key for {endpoint_name}")


def _append_jsonl(path: Path, payload: dict) -> None:
    with write_lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _compute_asv_score(request: AsvScoreRequest) -> float:
    # Baseline deterministic scoring for thesis integration pipeline.
    base = 1.0 - request.spoofProbability
    duration_bonus = min(max((request.recordingDurationSec - 1.0) * 0.03, 0.0), 0.1)

    digest = hashlib.sha256(str(request.sessionTimestampMs).encode("utf-8")).hexdigest()
    noise = (int(digest[:4], 16) / 65535.0 - 0.5) * 0.02

    score = base + duration_bonus + noise
    return float(min(max(score, 0.0), 1.0))


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/asv/score", response_model=AsvScoreResponse)
def asv_score(
    request: AsvScoreRequest,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> AsvScoreResponse:
    provided_key = _extract_api_key(authorization, x_api_key)
    _assert_auth(ASV_API_KEY, provided_key, "asv")

    score = _compute_asv_score(request)

    _append_jsonl(
        ASV_LOG_FILE,
        {
            "receivedAt": datetime.now(timezone.utc).isoformat(),
            "request": request.model_dump(),
            "asvScore": score,
            "source": "backend-baseline-v1",
        },
    )

    return AsvScoreResponse(asvScore=score, source="backend-baseline-v1")


@app.post("/api/telemetry/events")
def telemetry_events(
    event: TelemetryEvent,
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> dict:
    provided_key = _extract_api_key(authorization, x_api_key)
    _assert_auth(TELEMETRY_API_KEY, provided_key, "telemetry")

    _append_jsonl(
        TELEMETRY_LOG_FILE,
        {
            "receivedAt": datetime.now(timezone.utc).isoformat(),
            "event": event.model_dump(),
        },
    )

    return {"accepted": True}
