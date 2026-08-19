#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import tarfile
import tempfile
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


VIETSUPERSPEECH_BASE = "https://huggingface.co/datasets/thanhnew2001/VietSuperSpeech/resolve/main"
VIETTTS_TAR_URL = "https://huggingface.co/datasets/ntt123/viet-tts-dataset/resolve/main/viet-tts.tar.gz"


def download_url(url: str, output: Path, timeout: int = 60) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "fake-voice-detector-dataset-downloader/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response, tmp.open("wb") as f:
        shutil.copyfileobj(response, f)
    tmp.replace(output)


def download_vietsuperspeech_real(output_dir: Path, limit: int, workers: int) -> list[dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{VIETSUPERSPEECH_BASE}/dev.json", timeout=60) as response:
        records = json.loads(response.read().decode("utf-8"))

    rows: list[dict[str, str]] = []
    selected = records[:limit]

    def fetch(index_and_record: tuple[int, dict]) -> dict[str, str]:
        index, record = index_and_record
        audio_path = record["audio"]
        url_path = urllib.parse.quote(audio_path, safe="/")
        out = output_dir / f"real_{index:04d}_{Path(audio_path).name}"
        if not out.exists():
            download_url(f"{VIETSUPERSPEECH_BASE}/{url_path}", out)
        return {
            "path": str(out),
            "label": "bonafide",
            "source_dataset": "thanhnew2001/VietSuperSpeech",
            "source_path": audio_path,
            "text": record.get("text", ""),
        }

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch, item) for item in enumerate(selected)]
        for done, future in enumerate(as_completed(futures), start=1):
            rows.append(future.result())
            if done % 100 == 0 or done == len(futures):
                print(f"Downloaded/verified real files: {done}/{len(futures)}")
    rows.sort(key=lambda row: row["path"])
    return rows


def download_viettts_spoof(output_dir: Path, limit: int) -> list[dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    existing = sorted(output_dir.glob("spoof_*.wav"))
    for path in existing[:limit]:
        rows.append(
            {
                "path": str(path),
                "label": "spoof",
                "source_dataset": "ntt123/viet-tts-dataset",
                "source_path": path.name,
                "text": "",
            }
        )
    if len(rows) >= limit:
        return rows[:limit]

    with tempfile.NamedTemporaryFile(prefix="viet-tts-", suffix=".tar.gz") as tmp:
        print(f"Downloading synthetic Vietnamese TTS archive to temporary file: {tmp.name}")
        download_url(VIETTTS_TAR_URL, Path(tmp.name), timeout=600)
        with tarfile.open(tmp.name, mode="r:gz") as tar:
            for member in tar:
                if len(rows) >= limit:
                    break
                if not member.isfile() or not member.name.endswith(".wav"):
                    continue
                src_name = Path(member.name).name
                out = output_dir / f"spoof_{len(rows):04d}_{src_name}"
                if not out.exists():
                    extracted = tar.extractfile(member)
                    if extracted is None:
                        continue
                    with out.open("wb") as f:
                        shutil.copyfileobj(extracted, f)
                rows.append(
                    {
                        "path": str(out),
                        "label": "spoof",
                        "source_dataset": "ntt123/viet-tts-dataset",
                        "source_path": member.name,
                        "text": "",
                    }
                )
    return rows


def write_manifest(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label", "source_dataset", "source_path", "text"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Vietnamese external test data.")
    parser.add_argument("--output-root", type=Path, default=Path("data/external_vietnamese_test"))
    parser.add_argument("--limit-per-class", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--real-only", action="store_true")
    parser.add_argument("--spoof-only", action="store_true")
    args = parser.parse_args()

    if args.real_only and args.spoof_only:
        raise ValueError("Use at most one of --real-only or --spoof-only")

    rows: list[dict[str, str]] = []
    if not args.spoof_only:
        rows.extend(download_vietsuperspeech_real(args.output_root / "bonafide", args.limit_per_class, args.workers))
    if not args.real_only:
        rows.extend(download_viettts_spoof(args.output_root / "spoof", args.limit_per_class))

    write_manifest(rows, args.output_root / "manifest.csv")
    summary = {
        "output_root": str(args.output_root),
        "limit_per_class": args.limit_per_class,
        "count": len(rows),
        "bonafide": sum(1 for row in rows if row["label"] == "bonafide"),
        "spoof": sum(1 for row in rows if row["label"] == "spoof"),
        "sources": {
            "bonafide": "thanhnew2001/VietSuperSpeech dev.json",
            "spoof": "ntt123/viet-tts-dataset viet-tts.tar.gz",
        },
    }
    (args.output_root / "download_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
