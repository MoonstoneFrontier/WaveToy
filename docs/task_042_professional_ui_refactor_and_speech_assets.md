# Task 042 — Professional UI Refactor and Speech Assets Panel

## Design direction

WaveToy now moves away from a toy-like presentation toward a professional educational interface for high school students, college students, educators, speech-science learners, audio students, experimental musicians, and professionals exploring articulatory synthesis.

The interface keeps the WaveToy name and single-file `wave_toy.py` entry point, but the visual language is tightened around:

- compact but readable controls;
- reduced border thickness and corner radius;
- clearer section hierarchy;
- professional audio and speech terminology;
- denser toolbar rows;
- visible Speech Assets management;
- continuity with the existing Speech Bin data model for compatibility.

## Tab and navigation changes

Primary navigation has been renamed toward a more professional workflow:

1. **Synthesis** — fast play/performance controls.
2. **Wave Explorer** — waveform visualization and focused parameter panels.
3. **Articulation Lab** — phoneme and vocal-tract design.
4. **Graphical Editor** — direct manipulation workflow.
5. **Timeline** — audio-editor-style arrangement and export.
6. **Library** — central asset management.
7. **Classic Controls** — full legacy/fallback control surface.

The old capabilities remain accessible. Classic Controls is intentionally retained as the advanced fallback surface rather than removed.

## Speech Assets visibility

The existing Speech Bin data model remains intact internally, but the user-facing surface is now labeled **Speech Assets**.

Speech Assets is visible from:

- the **Articulation Lab** side panel;
- the **Timeline** asset drawer;
- the new **Library** tab.

The panel includes filters for:

- All;
- Phonemes;
- Syllables;
- Words;
- Phrases.

Cards show the asset name, type, duration, source/render mode, and phoneme sequence. Actions remain available for Preview, Rename, Add to Timeline, Duplicate, and Delete.

## Create Word feedback

After **Create Word**, the status path now communicates that the word was saved to **Speech Assets**. The created item is selected/highlighted by the existing selection model so users can immediately preview it or add it to the Timeline from any visible Speech Assets panel.

**Play Word** continues to preview the current render without creating duplicate Speech Assets.

## Label replacements

User-facing terminology was updated toward a professional tone:

| Previous label | New label |
| --- | --- |
| Speech Bin | Speech Assets |
| Audio Palette | Audio Assets |
| Timeline Storyboard | Timeline |
| Classic Editor | Classic Controls |
| Pitch Toys | Pitch Tools |
| Sound Magic | Texture / Effects |
| toy sound shelf | Audio Assets |

## Timeline cleanup

The Timeline header and toolbar now use compact professional labels such as Play, Stop, Render Mix, Add Sound, Add Lane, Add Voice Lane, Zoom In, and Zoom Out. The existing duration-accurate clip drawing, visible ruler, playhead, inspector, snap control, trim/stretch/split workflow, drag/drop, and export path remain intact.

## Articulation Timeline cleanup

The former chain workflow is presented as **Articulation Timeline** in the Articulation Lab. The existing time-based phoneme blocks, transition regions, duration/transition editing, and Word Motion Preview remain available with more technical wording around duration, transition, render mode, voice, airflow, closure, and burst concepts.

## Remaining legacy/toy labels intentionally left unchanged

Some internal identifiers and object names remain unchanged to reduce risk:

- `SpeechBinItem` and related `speech_bin` metadata keys are retained for saved-chain and Timeline compatibility.
- `StoryboardClipWidget` and `timelineStoryboard*` object names are retained as internal implementation names.
- `ToyButton`, `_toy_group`, and `_build_toy_title_banner` are retained as internal helper names to avoid a risky broad refactor.
- Pelog/slendro tooltip wording still uses "playful approximation" intentionally to clarify those tunings are approximate educational mappings, not authoritative cultural models.

## Known UI debt

- Some older helper class names still reflect the historic visual direction.
- The Timeline canvas object names still reference storyboard internally even though user-facing labels now say Timeline.
- The Phrases filter currently includes legacy chain assets because the saved data model uses `chain` for phrase-like rendered speech sequences.
- A deeper refactor could split `wave_toy.py` into modules, but that was intentionally avoided for this focused task.

## Suggested next professionalization phase

1. Rename internal helper classes and object names in a compatibility-safe pass.
2. Add non-modal toast feedback for Create Word and Add to Timeline.
3. Add a dedicated phrase asset creator distinct from raw chain assets.
4. Expand the Timeline inspector with editable start, end, duration, lane, gain, pan, and render-source fields.
5. Add visual focus/keyboard navigation polish for classrooms and accessibility audits.
