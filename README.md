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

## Waveform Source for Articulation

Articulation Lab can now treat a WaveToy waveform as the excitation/source that the mouth model shapes. A phoneme still defaults to the built-in voice/noise generator, but the user may assign one of these optional source modes per saved phoneme or per Articulation Chain item:

- **Default Voice** — uses the existing vowel, consonant, noise, closure, and burst generators.
- **Current WaveToy Sound** — uses the currently rendered Play/Mix Wave Shapes sound as the vocal source.
- **Selected Mix Wave** — renders one dynamic wave layer and uses it as the source; the current soloed layer is preferred, otherwise the first active layer is used.
- **Imported Audio Palette Item** — uses the selected Timeline Audio Palette item when available.

The shaping pipeline is: waveform source → trim or loop to phoneme duration → safe normalization and short fades → articulation formant/filter/envelope shaping → phoneme family behavior → output audio. Vowels and glides/liquids receive formant shaping, fricatives blend the source with filtered noise according to air pressure, stops preserve closure/burst behavior while using the source for voiced onset, and nasals apply low nasal resonance/softening.

Source metadata is saved with phoneme JSON and chain JSON as recipe/path settings only. Raw audio arrays are not embedded. Older phoneme files without source fields load as **Default Voice**. If a saved imported source path is missing at playback time, WaveToy warns the user and safely falls back to **Default Voice** for that render.

Arbitrary sci-fi waveforms can produce intentionally synthetic speech colors. Complex, noisy, or detuned sources may not preserve natural pitch or intelligibility as well as the default generator, but they remain useful for creature voices, robots, drones, and ambient vowel textures.

# WaveToy Long-Term Product Roadmap

## Vision

WaveToy is evolving from a waveform synthesizer into a Speech Workstation.

The long-term goal is to allow users to:

* Build speech
* Hear speech
* See speech
* Animate speech
* Export speech motion
* Create voice fonts
* Create singing voices
* Generate lip-sync and animation timing data

from a unified workflow.

WaveToy should remain approachable for hobbyists and students while also becoming useful to researchers, animators, educators, game developers, and content creators.

---

## Product Direction

WaveToy is expected to gradually become a hybrid of:

* Speech synthesis workstation
* Voice font creator
* Lip-sync authoring tool
* Speech science educational tool
* Animation timing editor
* Singing synthesis workstation
* Visual waveform and articulation editor

The project should avoid becoming a generic DAW and should remain focused on speech, articulation, and voice creation.

---

## Current Priority

The highest priority remains:

### Continuous Mouth Motion Quality

Before major expansion:

* Continuous Mouth Motion must produce stable pitch.
* Continuous Mouth Motion must avoid distortion.
* Continuous Mouth Motion must preserve stop bursts.
* Continuous Mouth Motion must preserve fricatives.
* Continuous Mouth Motion must sound better than Clip Crossfade.

Clip Crossfade remains the stable renderer.

Continuous Mouth Motion remains the primary development renderer.

---

## Timeline Direction

The Articulation Timeline is expected to become the primary editing surface.

Future editing should favor:

* Direct manipulation
* Visual editing
* Click-and-drag workflows
* Reduced dependence on inspector panels

The timeline should gradually evolve toward a speech workstation timeline.

---

## Planned Timeline Tracks

Long-term timeline architecture:

* Tempo Track
* Pitch Track
* Phoneme Track
* Accentuation Track
* Airflow Track
* Voicing Track
* Formant Track
* Viseme Track
* Animation Track

Initially only the Phoneme Track is required.

Additional tracks should be added gradually.

---

## Musical Timing Roadmap

WaveToy should eventually support both:

### Absolute Timing

* Milliseconds
* Seconds

### Musical Timing

* BPM
* Measures
* Beats
* Quantization
* Musical grids

Speech and singing should share a common timing architecture.

Future features:

* Tempo Track
* Pitch Lane
* Lyric Track
* Singing Mode
* MIDI Import
* MIDI Export
* Choir/Harmony Generation

---

## Voice Font Roadmap

Future workflow:

Voice Font Wizard

Stages:

1. Record phonemes
2. Record CV combinations
3. Record VC combinations
4. Record words
5. Record phrases
6. Analyze recordings
7. Generate voice profile
8. Export voice font

Voice font creation should remain explicit and user-driven.

WaveToy should not silently clone voices.

Consent and provenance tracking should be included.

---

## CV/VC Knowledge Base

WaveToy should maintain a complete library of:

* Consonant-Vowel combinations
* Vowel-Consonant combinations

Future uses:

* Voice font capture
* Continuous renderer tuning
* Speech research
* Pronunciation education
* Language learning

---

## Viseme Roadmap

WaveToy should generate viseme data from articulation data.

Future viseme outputs:

* Viseme Timeline
* Animation Curves
* Character Lip-Sync Data

Viseme generation should be driven by articulation and Continuous Mouth Motion state.

---

## Animation Export Roadmap

Future export targets:

* Blender
* Unity
* Godot
* Unreal
* VTuber rigs
* VRChat avatars

Export formats:

* JSON
* CSV
* Animation curves
* Timing tracks

Do not implement Blender-specific integrations before generic exports exist.

---

## SVG Roadmap

WaveToy should gradually migrate visual editing systems toward SVG-compatible rendering.

Future SVG systems:

* Waveform rendering
* Timeline rendering
* Articulation rendering
* Speech graphs

The SVG roadmap should support future web and tablet deployments.

---

## Educational Roadmap

Future educational features:

* IPA Explorer
* Language pronunciation trainer
* Speech articulation visualizer
* Phoneme comparison tools
* Accent comparison tools

WaveToy should be useful for learning speech production.

---

## Research Roadmap

Future research features:

* Coarticulation database
* Transition analysis
* Phoneme feature vectors
* Articulation datasets
* Voice comparison tools

These should be optional and not complicate core workflows.

---

## Export Package Roadmap

Future exports may include:

* Audio
* Articulation recipe
* Diagnostics
* Viseme data
* Provenance manifest

All export formats should be human-readable whenever practical.

---

## Do Not Build Yet

The following remain future work:

* Production voice cloning
* Cloud services
* Online sharing platform
* Blender addon
* Large-scale machine learning systems
* Major repository modularization
* Web rewrite

Focus first on:

1. Continuous Mouth Motion quality
2. Articulation Timeline workflow
3. Speech workstation usability
4. Viseme foundations
5. Voice font foundations
6. Musical timing foundations

before pursuing larger expansions.

