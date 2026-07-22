#!/usr/bin/env python3
"""
Chuẩn bị dataset từ nhiều nguồn khác nhau cho pipeline huấn luyện.

Hỗ trợ:
  1. Kaggle "The Fake or Real Dataset" (FOR) — for-norm hoặc for-original
  2. Thư mục WAV tùy chỉnh (bonafide/ + spoof/)
  3. Demo mode — dùng TTS từ mc_thu_hue_fix_char làm spoof +
     tạo tín hiệu tổng hợp làm bonafide (CHỈ để kiểm thử pipeline,
     KHÔNG dùng cho đề tài thật)

Cách dùng:
  # Kaggle FOR dataset
  python prepare_dataset.py --mode kaggle --source /path/to/for-norm --output data/dataset_samples

  # Chế độ demo (không cần data thật)
  python prepare_dataset.py --mode demo --spoof-source resources/mc_thu_hue_fix_char/wavs --output data/dataset_samples
"""
from __future__ import annotations

import argparse
import math
import os
import shutil
import struct
import wave
from pathlib import Path
from typing import List


# ─── Helpers ─────────────────────────────────────────────────────────────────

def copy_wavs(src_dirs: List[Path], dst_dir: Path, label: str, limit: int = 0) -> int:
    dst_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for src_dir in src_dirs:
        if not src_dir.exists():
            continue
        files = sorted(src_dir.rglob("*.wav"))
        if limit:
            files = files[:max(0, limit - count)]
        for src in files:
            dst = dst_dir / f"{label}_{src.stem[:60]}.wav"
            if dst.exists():
                dst = dst_dir / f"{label}_{src.stem[:55]}_{count}.wav"
            shutil.copy2(src, dst)
            count += 1
            if limit and count >= limit:
                return count
    return count


def write_wav_int16(path: Path, samples: List[float], sample_rate: int = 16000) -> None:
    """Ghi danh sách float [-1, 1] ra file WAV 16-bit mono."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        pcm = struct.pack(f"<{len(samples)}h", *[
            max(-32768, min(32767, int(s * 32767))) for s in samples
        ])
        wf.writeframes(pcm)


def make_synthetic_bonafide(path: Path, duration_sec: float = 3.0, sr: int = 16000) -> None:
    """
    Tạo tín hiệu giả lập giọng người (multi-harmonic + tremolo + noise).

    CHÚ Ý: Chỉ dùng để kiểm thử pipeline — KHÔNG đại diện cho giọng người thật.
    Đối với nghiên cứu thực sự, cần dùng bản ghi âm giọng người thật.
    """
    n = int(duration_sec * sr)
    f0 = 130.0  # tần số cơ bản (Hz), phổ biến cho giọng nam
    tremolo_rate = 5.5  # Hz

    samples: List[float] = []
    for i in range(n):
        t = i / sr
        # Tổng hợp nhiều harmonic (giọng người có nhiều overtone tự nhiên)
        voice = (
            0.40 * math.sin(2 * math.pi * f0 * t) +
            0.25 * math.sin(2 * math.pi * f0 * 2 * t) +
            0.15 * math.sin(2 * math.pi * f0 * 3 * t) +
            0.10 * math.sin(2 * math.pi * f0 * 4 * t) +
            0.05 * math.sin(2 * math.pi * f0 * 5 * t)
        )
        # Tremolo (biến động biên độ tự nhiên)
        env = 0.85 + 0.15 * math.sin(2 * math.pi * tremolo_rate * t)
        # Nhiễu nền nhỏ
        noise = ((hash((i * 2654435761) & 0xFFFFFFFF) % 2001) / 2000.0 - 0.5) * 0.04
        samples.append(voice * env * 0.7 + noise)

    write_wav_int16(path, samples, sr)


# ─── Mode: Kaggle FOR dataset ─────────────────────────────────────────────────

def prepare_kaggle(source_root: Path, output_root: Path, limit_per_class: int) -> None:
    """
    Dataset "The Fake or Real" (FOR) trên Kaggle có cấu trúc:
      for-norm/
        training/real/*.wav
        training/fake/*.wav
        validation/real/*.wav
        validation/fake/*.wav
        testing/real/*.wav
        testing/fake/*.wav

    Script này gộp tất cả split lại vào bonafide/ và spoof/ để
    train_spoof_model.py tự chia lại theo tỷ lệ 60-20-20.
    """
    splits = ["training", "validation", "testing"]
    bonafide_dirs = [source_root / s / "real" for s in splits]
    spoof_dirs    = [source_root / s / "fake" for s in splits]

    out_bonafide = output_root / "bonafide"
    out_spoof    = output_root / "spoof"

    n_b = copy_wavs(bonafide_dirs, out_bonafide, "bonafide", limit_per_class)
    n_s = copy_wavs(spoof_dirs,    out_spoof,    "spoof",    limit_per_class)

    print(f"Kaggle FOR dataset chuẩn bị xong:")
    print(f"  bonafide : {n_b} files → {out_bonafide}")
    print(f"  spoof    : {n_s} files → {out_spoof}")


# ─── Mode: Custom directory ───────────────────────────────────────────────────

def prepare_custom(bonafide_src: Path, spoof_src: Path, output_root: Path, limit_per_class: int) -> None:
    out_bonafide = output_root / "bonafide"
    out_spoof    = output_root / "spoof"
    n_b = copy_wavs([bonafide_src], out_bonafide, "bonafide", limit_per_class)
    n_s = copy_wavs([spoof_src],    out_spoof,    "spoof",    limit_per_class)
    print(f"Custom dataset chuẩn bị xong:")
    print(f"  bonafide : {n_b} files → {out_bonafide}")
    print(f"  spoof    : {n_s} files → {out_spoof}")


# ─── Mode: Demo (pipeline test only) ─────────────────────────────────────────

def prepare_demo(
    spoof_source_dir: Path,
    output_root: Path,
    n_spoof: int,
    n_bonafide: int,
    sr: int,
) -> None:
    """
    Tạo dataset demo:
      - Spoof: lấy từ thư mục TTS có sẵn (mc_thu_hue_fix_char/wavs)
      - Bonafide: tạo tín hiệu tổng hợp (CHỈ để test pipeline)

    QUAN TRỌNG: Dataset này không phù hợp cho đề tài thực sự.
    Model train từ đây chỉ để xác nhận pipeline end-to-end hoạt động.
    Cần thay thế bằng dữ liệu thật (Kaggle FOR dataset) trước khi báo cáo.
    """
    print("⚠  DEMO MODE — dataset này chỉ để kiểm thử pipeline!")
    print("   Không dùng model này trong đề tài thực tế.\n")

    out_bonafide = output_root / "bonafide"
    out_spoof    = output_root / "spoof"
    out_bonafide.mkdir(parents=True, exist_ok=True)
    out_spoof.mkdir(parents=True, exist_ok=True)

    # Spoof: copy từ TTS source
    n_s = copy_wavs([spoof_source_dir], out_spoof, "spoof", n_spoof)

    # Bonafide: tạo tổng hợp
    print(f"Đang tạo {n_bonafide} mẫu bonafide tổng hợp...")
    durations = [2.0, 2.5, 3.0, 3.5, 4.0]
    pitches   = [110, 130, 150, 180, 200]  # Hz — giọng thấp/cao
    for i in range(n_bonafide):
        dur = durations[i % len(durations)]
        f0  = pitches[i % len(pitches)]
        n   = int(dur * sr)
        tremolo = 5.0 + (i % 5)
        samples = []
        for j in range(n):
            t = j / sr
            v = (
                0.40 * math.sin(2 * math.pi * f0 * t) +
                0.25 * math.sin(2 * math.pi * f0 * 2 * t) +
                0.15 * math.sin(2 * math.pi * f0 * 3 * t) +
                0.10 * math.sin(2 * math.pi * f0 * 4 * t) +
                0.05 * math.sin(2 * math.pi * f0 * 5 * t)
            )
            env = 0.85 + 0.15 * math.sin(2 * math.pi * tremolo * t)
            noise = ((hash((j * 2654435761 + i) & 0xFFFFFFFF) % 2001) / 2000.0 - 0.5) * 0.04
            samples.append(v * env * 0.7 + noise)
        write_wav_int16(out_bonafide / f"bonafide_synth_{i:04d}.wav", samples, sr)

    print(f"Demo dataset chuẩn bị xong:")
    print(f"  bonafide : {n_bonafide} files (tổng hợp) → {out_bonafide}")
    print(f"  spoof    : {n_s} files (TTS) → {out_spoof}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chuẩn bị dataset cho pipeline huấn luyện anti-spoof"
    )
    parser.add_argument(
        "--mode", required=True, choices=["kaggle", "custom", "demo"],
        help="kaggle=FOR dataset | custom=thư mục tùy ý | demo=chỉ test pipeline"
    )
    parser.add_argument("--source",         type=Path, default=None, help="Thư mục gốc dataset Kaggle FOR")
    parser.add_argument("--bonafide-src",   type=Path, default=None, help="[custom] Thư mục bonafide WAV")
    parser.add_argument("--spoof-src",      type=Path, default=None, help="[custom/demo] Thư mục spoof WAV")
    parser.add_argument("--output",         type=Path, default=Path("data/dataset_samples"))
    parser.add_argument("--limit",          type=int,  default=0,    help="Giới hạn số file mỗi lớp (0=không giới hạn)")
    parser.add_argument("--demo-n-spoof",   type=int,  default=200,  help="[demo] Số file spoof")
    parser.add_argument("--demo-n-bonafide",type=int,  default=200,  help="[demo] Số file bonafide tổng hợp")
    parser.add_argument("--sr",             type=int,  default=16000, help="Sample rate mục tiêu")
    args = parser.parse_args()

    if args.mode == "kaggle":
        if not args.source:
            parser.error("--source là bắt buộc với --mode kaggle")
        prepare_kaggle(args.source, args.output, args.limit)

    elif args.mode == "custom":
        if not args.bonafide_src or not args.spoof_src:
            parser.error("--bonafide-src và --spoof-src là bắt buộc với --mode custom")
        prepare_custom(args.bonafide_src, args.spoof_src, args.output, args.limit)

    elif args.mode == "demo":
        spoof_src = args.spoof_src
        if not spoof_src:
            # Dùng mc_thu_hue_fix_char mặc định
            spoof_src = Path("resources/mc_thu_hue_fix_char/wavs")
        if not spoof_src.exists():
            parser.error(f"Không tìm thấy thư mục spoof source: {spoof_src}")
        prepare_demo(spoof_src, args.output, args.demo_n_spoof, args.demo_n_bonafide, args.sr)


if __name__ == "__main__":
    main()
