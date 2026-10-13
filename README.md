# Voice Isolator

A free script that removes music and background noise from a video and keeps only the voice. It runs locally on your computer. No subscription, no uploads to other servers.

## How it works

1. Extracts the audio from the video (ffmpeg).
2. The **BS-Roformer** AI model separates the voice from the music.
3. The **Mel-Roformer DeNoise** AI model removes the remaining noise from the voice.
4. Normalizes loudness (loudnorm, -16 LUFS).
5. Puts the clean voice back into the video **without re-encoding the picture**, so the video quality stays 100% the same.

On a test video (4 min, 1080p), the background in the pauses between words dropped from -25.7 dB to -63.9 dB, which is almost full silence.

## Installation

You only need [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
winget install astral-sh.uv
```

The script downloads everything else (Python, PyTorch, ffmpeg, AI models) on the first run. The first run takes longer because it downloads about 4 GB.

## Usage

**Windows, easiest way:** drag and drop a video onto `voice_isolator.bat`.

**Terminal:**

```bash
uv run --python 3.12 --script voice_isolator.py "path/to/video.mp4"
```

Options:

| Option | What it does |
|---|---|
| `--no-denoise` | Skip noise removal (faster, removes music only) |
| `--output DIR` | Where to save the results (default: next to the video) |

Results:

| File | Content |
|---|---|
| `<name>_voice_only.mp4` | Video with the clean voice |
| `<name>_voice_only.wav` | Voice only, uncompressed |
| `<name>_voice_only.mp3` | Voice only, 320 kbps |

## Requirements and speed

- Windows or Linux. An NVIDIA GPU (CUDA) is recommended. It also works without one, but much slower.
- On an RTX 3050, a 4-minute video takes about 20 minutes. Close games and other programs that use the GPU while processing.
- You can ignore the `onnxruntime` / `cudart64_13.dll` warning in the log. The models run on PyTorch.

## Credits

- [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator) for running the models
- BS-Roformer model by viperx, Mel-Roformer DeNoise model by aufr33. The models are downloaded from their original sources and keep their own licenses.
- [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) for the bundled ffmpeg

## License

[MIT](LICENSE)
