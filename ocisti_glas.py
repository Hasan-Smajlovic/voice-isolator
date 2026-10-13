# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "audio-separator[gpu]>=0.30",
#   "audioread>=3.0",
#   "imageio-ffmpeg>=0.5",
#   "torch>=2.4",
#   "torchaudio>=2.4",
# ]
#
# [tool.uv.sources]
# torch = { index = "pytorch-cu124" }
# torchaudio = { index = "pytorch-cu124" }
#
# [[tool.uv.index]]
# name = "pytorch-cu124"
# url = "https://download.pytorch.org/whl/cu124"
# explicit = true
# ///
"""
Ocisti glas iz videa: uklanja muziku i pozadinsku buku, ostavlja samo glas.

Koraci:
  1. Izvuce zvuk iz videa (ffmpeg).
  2. AI model (BS-Roformer) odvoji glas od muzike.
  3. Drugi AI model (Mel-Roformer DeNoise) ukloni preostalu buku iz glasa.
  4. Izjednaci glasnocu (loudnorm, -16 LUFS).
  5. Vrati cisti glas u video BEZ ponovnog kodiranja slike (kvalitet slike ostaje 100% isti).

Upotreba:
  uv run ocisti_glas.py "C:\\putanja\\do\\videa.mp4"
  uv run ocisti_glas.py video.mp4 --bez-denoise      (samo uklanjanje muzike)
  uv run ocisti_glas.py video.mp4 --izlaz D:\\Rezultati

Rezultati (pored videa ili u --izlaz folderu):
  <ime>_samo_glas.mp4   video sa cistim glasom
  <ime>_samo_glas.wav   samo glas, bez kompresije (najbolji kvalitet)
  <ime>_samo_glas.mp3   samo glas, 320 kbps
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import imageio_ffmpeg

VOCAL_MODEL = "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
DENOISE_MODEL = "denoise_mel_band_roformer_aufr33_sdr_27.9959.ckpt"
MODEL_DIR = Path.home() / ".cache" / "ocisti_glas_modeli"

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def expose_ffmpeg_on_path() -> None:
    """audio-separator calls plain `ffmpeg`, so expose the bundled binary under that name."""
    if shutil.which("ffmpeg"):
        return
    bin_dir = MODEL_DIR / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target = bin_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if not target.exists():
        shutil.copy2(FFMPEG, target)
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"


def ffmpeg(*args: str) -> None:
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *args]
    subprocess.run(cmd, check=True)


def separate(audio: Path, model: str, keep_stem: str, out_dir: Path) -> Path:
    """Run one audio-separator model and return the path of the stem we want."""
    from audio_separator.separator import Separator

    separator = Separator(
        model_file_dir=str(MODEL_DIR),
        output_dir=str(out_dir),
        output_format="WAV",
        output_single_stem=keep_stem,
        # Library default overlap is 8 (each chunk processed 8x); 4 is indistinguishable and ~2x faster.
        mdxc_params={"segment_size": 256, "override_model_segment_size": False, "batch_size": 1, "overlap": 4, "pitch_shift": 0},
    )
    separator.load_model(model_filename=model)
    outputs = separator.separate(str(audio))
    wanted = [name for name in outputs if f"({keep_stem.lower()})" in name.lower()]
    if not wanted:
        raise RuntimeError(f"Model {model} nije vratio '{keep_stem}' stem, dobio: {outputs}")
    return out_dir / Path(wanted[0]).name


def main() -> int:
    parser = argparse.ArgumentParser(description="Ukloni muziku i buku iz videa, ostavi samo glas.")
    parser.add_argument("video", type=Path, help="Putanja do videa (mp4, mov, mkv...)")
    parser.add_argument("--izlaz", type=Path, help="Folder za rezultate (default: pored videa)")
    parser.add_argument("--bez-denoise", action="store_true", help="Preskoci drugi korak (uklanjanje buke)")
    args = parser.parse_args()

    video: Path = args.video.resolve()
    if not video.is_file():
        print(f"Video ne postoji: {video}", file=sys.stderr)
        return 1

    out_dir = (args.izlaz or video.parent).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = video.stem
    out_video = out_dir / f"{stem}_samo_glas{video.suffix}"
    out_wav = out_dir / f"{stem}_samo_glas.wav"
    out_mp3 = out_dir / f"{stem}_samo_glas.mp3"

    expose_ffmpeg_on_path()
    start = time.time()
    with tempfile.TemporaryDirectory(prefix="ocisti_glas_") as tmp_str:
        tmp = Path(tmp_str)

        print("[1/5] Izvlacim zvuk iz videa...")
        original = tmp / "original.wav"
        ffmpeg("-i", str(video), "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(original))

        print("[2/5] Odvajam glas od muzike (BS-Roformer)...")
        voice = separate(original, VOCAL_MODEL, "Vocals", tmp)

        if args.bez_denoise:
            print("[3/5] Preskacem uklanjanje buke (--bez-denoise).")
        else:
            print("[3/5] Uklanjam preostalu buku iz glasa (Mel-Roformer DeNoise)...")
            voice = separate(voice, DENOISE_MODEL, "dry", tmp)

        print("[4/5] Izjednacavam glasnocu...")
        ffmpeg(
            "-i", str(voice),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "48000", "-c:a", "pcm_s24le",
            str(out_wav),
        )
        ffmpeg("-i", str(out_wav), "-c:a", "libmp3lame", "-b:a", "320k", str(out_mp3))

        print("[5/5] Vracam cisti glas u video (slika se ne dira)...")
        ffmpeg(
            "-i", str(video), "-i", str(out_wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
            "-shortest", "-movflags", "+faststart",
            str(out_video),
        )

    minutes, seconds = divmod(int(time.time() - start), 60)
    print(f"\nGotovo za {minutes}m {seconds}s. Rezultati:")
    for path in (out_video, out_wav, out_mp3):
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
