# Očisti glas

Besplatna skripta koja iz videa uklanja muziku i pozadinsku buku i ostavlja samo glas. Radi lokalno na tvom računaru, bez pretplate i bez uploada na tuđe servere.

*English below.*

## Kako radi

1. Izvuče zvuk iz videa (ffmpeg).
2. AI model **BS-Roformer** odvoji glas od muzike.
3. AI model **Mel-Roformer DeNoise** ukloni preostalu buku iz glasa.
4. Izjednači glasnoću (loudnorm, -16 LUFS).
5. Vrati čisti glas u video **bez ponovnog kodiranja slike**, tako da kvalitet slike ostaje 100% isti.

Na testnom videu (4 min, 1080p) pozadina u pauzama govora je spuštena sa -25.7 dB na -63.9 dB, tj. praktično tišina.

## Instalacija

Potreban je samo [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
winget install astral-sh.uv
```

Sve ostalo (Python, PyTorch, ffmpeg, AI modeli) skripta sama skine pri prvom pokretanju. Prvo pokretanje traje duže jer se skida oko 4 GB.

## Upotreba

**Windows, najlakše:** prevuci video na `ocisti_glas.bat`.

**Terminal:**

```bash
uv run --python 3.12 --script ocisti_glas.py "C:\put\do\videa.mp4"
```

Opcije:

| Opcija | Šta radi |
|---|---|
| `--bez-denoise` | Preskoči uklanjanje buke (brže, uklanja samo muziku) |
| `--izlaz FOLDER` | Gdje da sačuva rezultate (default: pored videa) |

Rezultati:

| Fajl | Sadržaj |
|---|---|
| `<ime>_samo_glas.mp4` | Video sa čistim glasom |
| `<ime>_samo_glas.wav` | Samo glas, bez kompresije |
| `<ime>_samo_glas.mp3` | Samo glas, 320 kbps |

## Zahtjevi i brzina

- Windows ili Linux. Preporučena NVIDIA grafička (CUDA). Radi i bez nje, ali dosta sporije.
- Na RTX 3050 video od 4 minute traje oko 20 minuta. Ugasi igrice i druge programe koji koriste grafičku dok obrađuješ.
- Upozorenje o `onnxruntime` / `cudart64_13.dll` u logu se može ignorisati, modeli rade preko PyTorch-a.

---

## English

A free script that removes music and background noise from a video and keeps only the voice. Runs locally, no subscription, no uploads.

**Pipeline:** extract audio with ffmpeg, separate vocals with BS-Roformer, remove leftover noise with Mel-Roformer DeNoise, normalize loudness, then remux the clean voice into the video with the video stream copied (no re-encode, no quality loss).

**Install:** just [uv](https://docs.astral.sh/uv/getting-started/installation/). Everything else is fetched on first run (~4 GB).

**Run:**

```bash
uv run --python 3.12 --script ocisti_glas.py "path/to/video.mp4"
```

On Windows you can also drag a video onto `ocisti_glas.bat`. Flags: `--bez-denoise` (skip denoise, faster), `--izlaz DIR` (output folder). Outputs `<name>_samo_glas.mp4`, `.wav` and `.mp3` next to the video.

**Requirements:** Windows or Linux, NVIDIA GPU recommended (CPU works but is much slower).

## Zahvale / Credits

- [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator) for running the models
- BS-Roformer model by viperx, Mel-Roformer DeNoise model by aufr33. The models are downloaded from their original sources and keep their own licenses.
- [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) for the bundled ffmpeg

## Licenca / License

[MIT](LICENSE)
