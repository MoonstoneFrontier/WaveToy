# WaveToy

WaveToy is a Python desktop audio/sci-fi soundscape generator centered on a single PySide6 GUI script. It is currently an educational waveform synthesizer for exploring sound waves, musical tuning, stereo motion, file export, and experimental Paulstretch-style ambience.

This repository also includes a small localhost-first Flask lead workflow used for operational UI cleanup tasks. It stores lead workflow state in local JSON and does not add scraping, OCR, GIS overlays, email sending, external databases, or live source integrations.

## Current WaveToy entry point

Run the desktop audio app from:

```bash
python wave_toy.py
```

`wave_toy.py` defines `main()` and executes it under the standard `if __name__ == "__main__"` guard. Preserve this script name as the primary WaveToy entry point unless a future task explicitly changes it.

`wave_toy_single_module.py` is also present and appears to contain a similar single-file implementation snapshot. Treat `wave_toy.py` as the active WaveToy entry point for now.

## Local lead workflow entry point

Run the localhost workflow UI from:

```bash
python run_dev.py
```

Copy `.env.example` to `.env` for local development if you need to override the default host, port, logging flags, browser behavior, or Flask secret key.

## Dependencies

Install dependencies from `requirements.txt` before running tests. The `pytest` command requires the Flask, python-dotenv, and pytest dependencies from `requirements.txt` to be installed in the active environment.

WaveToy runtime dependencies include:

- `PySide6` — GUI framework
- `numpy` — audio/waveform array processing
- `sounddevice` — optional direct audio playback; the app falls back when unavailable

Optional export support for MP3/OGG/FLAC requires installing the `ffmpeg` executable with your operating system package manager and ensuring it is available on `PATH`.

## Quick start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest
python run_dev.py
```

## Safe verification

Before finalizing Python changes, run syntax checks for the touched modules:

```bash
python -m py_compile wave_toy.py
python3 -m py_compile app/main.py app/services/lead_pipeline_service.py app/services/lead_dedupe_service.py app/services/lead_transition_service.py
```

For dependency visibility in a fresh environment, check whether the imported third-party packages are installed:

```bash
python - <<'PY'
import importlib.util
for package in ['numpy', 'PySide6', 'sounddevice', 'flask', 'dotenv', 'pytest']:
    print(f'{package}:', 'found' if importlib.util.find_spec(package) else 'missing')
PY
```

## Known current issues

- Long-running Paulstretch playback has recently not stopped reliably.
- Stop/cancel behavior, playback lifecycle control, and UI responsiveness need focused follow-up work.
- Debug logging is not yet formalized for audio lifecycle events.
- `sounddevice` and `ffmpeg` availability varies by local machine, so playback/export behavior may differ by environment.

## Future development notes

- Prefer small, reviewable patches with clear before/after verification.
- Do not remove existing audio generation features without explicit approval.
- Preserve `wave_toy.py` as the main script name unless instructed otherwise.
- Prioritize audio lifecycle control, cancellation, debug logging, and responsiveness in upcoming tasks.
- Avoid introducing large new dependencies unless they are clearly required and documented.
