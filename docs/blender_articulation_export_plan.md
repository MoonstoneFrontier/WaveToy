# Blender Articulation Export Plan

WaveToy's articulation timeline can eventually export speech and mouth-motion data for Blender rigs. This foundation task adds a JSON export schema stub only; it does not ship a Blender add-on or rig integration.

## Proposed export formats

- JSON for structured animation curves.
- CSV for spreadsheet or simple timeline inspection.
- A future Blender add-on import format that maps WaveToy fields to rig-specific custom properties or shape keys.

## Proposed JSON schema

- `fps`
- `duration_seconds`
- `phoneme_blocks`
- `viseme_blocks`
- `mouth_open_curve`
- `tongue_height_curve`
- `tongue_frontness_curve`
- `lip_rounding_curve`
- `jaw_curve`
- `voicing_curve`
- `airflow_curve`
- `nasal_open_curve`

## Rig mapping direction

- Mouth open and jaw curves map to jaw rotation or mouth-open shape keys.
- Lip rounding maps to pursed or rounded lip shapes.
- Tongue height/frontness can drive custom tongue controls when the rig supports them.
- Voicing and airflow curves can drive visual vibration, breath, or subtitle cues.
- Nasal opening can drive stylized nose or soft-palate controls where available.

## Stub added in `wave_toy.py`

- `export_articulation_animation_json()`

## Future work

- Export the live Articulation Timeline chain into the schema.
- Add viseme grouping presets.
- Add Blender add-on importer and rig mapping profiles.
- Add curve simplification and frame-rate conversion.
