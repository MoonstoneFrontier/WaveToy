# Task 058: Continuous Validation, Phoneme Inventory, Compact Workflow

## Summary

Task 058 makes Continuous Mouth Motion visible and testable, expands the English phoneme presets, completes the generated CV/VC inventory, and compacts Articulation/Graphical workflows without changing the main `wave_toy.py` entry point.

## Continuous Mouth Motion

Continuous Mouth Motion remains the primary development renderer. Clip Crossfade remains the stable default and the recommended CV/VC render mode until Continuous validation is consistently healthy.

The Articulation Timeline now provides a diagnostics panel and a Validate Continuous button. Terminal debug output is preserved, while normal failures such as low output, silent buffers, or missing voiced paths are shown in the panel instead of modal warnings.

## Articulation Lab action placement

`Save Phoneme` and `Add to Articulation Timeline` are stacked vertically in the current-phoneme action area immediately above the preset selector/phoneme drawer. Tooltips describe the exact action for each button.

## Graphical Editor compaction

The Graphical Editor keeps global vertical scrolling but reduces bulky card margins, oversized action buttons, and canvas minimums. Source Wave actions remain above the graph/layer cards they modify, with wrapping button rows to reduce horizontal overflow on common laptop widths.

## English phoneme inventory

The preset inventory includes common English monophthongs, diphthongs, stops, affricates, fricatives, nasals, liquids, and glides. Legacy aliases such as `EE`, `OH`, and `OO` remain compatible with saved chains and validation prompts.

## CV/VC library

The library is generated from 24 consonants and 16 vowels for 768 total CV/VC combinations. Entries keep Clip Crossfade as the recommended stable render mode and include Continuous tuning fields for future renderer work.

## Future work preserved

- voice font recording workflow
- recording prompt dataset
- viseme mapping
- Blender animation export
- provenance manifest integration
- editable fade handles
- higher quality Continuous Mouth Motion synthesis
