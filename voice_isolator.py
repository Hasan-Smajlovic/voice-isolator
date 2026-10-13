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
Voice isolator: removes music and background noise from a video and keeps only the voice.

Steps:
  1. Extract the audio from the video (ffmpeg).
  2. An AI model (BS-Roformer) separates the voice from the music.
  3. A second AI model (Mel-Roformer DeNoise) removes the remaining noise from the voice.
  4. Normalize loudness (loudnorm, -16 LUFS).
  5. Put the clean voice back into the video WITHOUT re-encoding the picture (video quality stays 100% the same).

Usage:
  uv run voice_isolator.py "C:\\path\\to\\video.mp4"
  uv run voice_isolator.py video.mp4 --no-denoise      (remove music only)
  uv run voice_isolator.py video.mp4 --output D:\\Results

Results (next to the video, or in the --output folder):
  <name>_voice_only.mp4   video with the clean voice
  <name>_voice_only.wav   voice only, uncompressed (best quality)
  <name>_voice_only.mp3   voice only, 320 kbps
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
MODEL_DIR = Path.home() / ".cache" / "voice_isolator_models"

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
        raise RuntimeError(f"Model {model} did not return the '{keep_stem}' stem, got: {outputs}")
    return out_dir / Path(wanted[0]).name


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove music and noise from a video, keep only the voice.")
    parser.add_argument("video", type=Path, help="Path to the video (mp4, mov, mkv...)")
    parser.add_argument("--output", type=Path, help="Folder for the results (default: next to the video)")
    parser.add_argument("--no-denoise", action="store_true", help="Skip the second step (noise removal)")
    args = parser.parse_args()

    video: Path = args.video.resolve()
    if not video.is_file():
        print(f"Video not found: {video}", file=sys.stderr)
        return 1

    out_dir = (args.output or video.parent).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = video.stem
    out_video = out_dir / f"{stem}_voice_only{video.suffix}"
    out_wav = out_dir / f"{stem}_voice_only.wav"
    out_mp3 = out_dir / f"{stem}_voice_only.mp3"

    expose_ffmpeg_on_path()
    start = time.time()
    with tempfile.TemporaryDirectory(prefix="voice_isolator_") as tmp_str:
        tmp = Path(tmp_str)

        print("[1/5] Extracting audio from the video...")
        original = tmp / "original.wav"
        ffmpeg("-i", str(video), "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(original))

        print("[2/5] Separating voice from music (BS-Roformer)...")
        voice = separate(original, VOCAL_MODEL, "Vocals", tmp)

        if args.no_denoise:
            print("[3/5] Skipping noise removal (--no-denoise).")
        else:
            print("[3/5] Removing remaining noise from the voice (Mel-Roformer DeNoise)...")
            voice = separate(voice, DENOISE_MODEL, "dry", tmp)

        print("[4/5] Normalizing loudness...")
        ffmpeg(
            "-i", str(voice),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "48000", "-c:a", "pcm_s24le",
            str(out_wav),
        )
        ffmpeg("-i", str(out_wav), "-c:a", "libmp3lame", "-b:a", "320k", str(out_mp3))

        print("[5/5] Putting the clean voice back into the video (picture is not re-encoded)...")
        ffmpeg(
            "-i", str(video), "-i", str(out_wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
            "-shortest", "-movflags", "+faststart",
            str(out_video),
        )

    minutes, seconds = divmod(int(time.time() - start), 60)
    print(f"\nDone in {minutes}m {seconds}s. Results:")
    for path in (out_video, out_wav, out_mp3):
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
