# Task 100: WaveToy Data Directory

WaveToy now resolves a user data root outside the application source tree before creating project, asset, export, cache, recovery, phoneme, animation, or viseme files.

## Resolution order

1. `WAVETOY_DATA_DIR`, when set.
2. A saved `data_root` in the local app config file.
3. The platform default `WaveToyData` path, such as `$XDG_DATA_HOME/WaveToyData` or `~/.local/share/WaveToyData` on Linux.
4. In interactive GUI sessions where no saved directory exists, WaveToy prompts the user to choose a durable directory. The first-run prompt suggests `/home/moonstone/Wave_Toy_Projects` when that user/path applies, otherwise `~/Wave_Toy_Projects`.

The saved config lives at `~/.config/WaveToy/settings.json` on Linux, or under `WAVETOY_CONFIG_DIR` when that environment variable is set. The file stores `data_root`, `selected_at`, and `version`.

## Data layout

WaveToy creates these top-level folders under the selected data root:

- `Projects/`
- `Assets/`
- `Exports/`
- `Cache/`
- `Recovery/`
- `LegacyImports/`
- `Audio/`
- `Voices/`
- `Words/`
- `Phonemes/`
- `Animations/`
- `Visemes/`

## Manual migration note

If old repo-local generated folders such as `phonemes/`, `audio_files/`, `animations/`, `visemes/`, `Chords/`, root audio exports, or `articulation_chain.json` exist beside `wave_toy.py`, WaveToy logs a non-blocking warning and suggests moving them to `LegacyImports/` under the active data root.

WaveToy does **not** automatically move those files yet. A future guided migration task can add confirmation UI and copy/move validation.
