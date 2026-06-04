import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def _display(notes, root="A", spelling="Auto"):
    return wave_toy.display_pitch_class_set(notes, root, spelling)


def test_a_major_scale_returns_expected_pitch_classes_and_names():
    notes = wave_toy.scale_pitch_classes("A", "major")
    assert notes == ["A", "B", "C#", "D", "E", "F#", "G#"]
    assert _display(notes, "A", "Auto") == ["A", "B", "C#", "D", "E", "F#", "G#"]


def test_bb_major_scale_displays_flats_in_auto_mode():
    notes = wave_toy.scale_pitch_classes("Bb", "major")
    assert notes == ["A#", "C", "D", "D#", "F", "G", "A"]
    assert _display(notes, "Bb", "Auto") == ["Bb", "C", "D", "Eb", "F", "G", "A"]


def test_a_natural_minor_returns_expected_notes():
    notes = wave_toy.scale_pitch_classes("A", "natural_minor")
    assert notes == ["A", "B", "C", "D", "E", "F", "G"]
    assert _display(notes, "A", "Auto") == ["A", "B", "C", "D", "E", "F", "G"]


def test_foundational_chords_return_expected_notes():
    assert wave_toy.chord_pitch_classes("A", "major_triad") == ["A", "C#", "E"]
    assert wave_toy.chord_pitch_classes("A", "minor_triad") == ["A", "C", "E"]
    assert wave_toy.chord_pitch_classes("A", "dominant_7") == ["A", "C#", "E", "G"]


def test_scale_and_chord_degrees():
    assert wave_toy.scale_degree_for_note("C#", "A", "major") == 3
    assert wave_toy.scale_degree_for_note("C", "A", "natural_minor") == 3
    assert wave_toy.chord_degree_for_note("E", "A", "major_triad") == 5
    assert wave_toy.scale_degree_for_note("C", "A", "major") is None


def test_display_spelling_respects_sharps_and_flats_without_changing_pitch_classes():
    notes = ["A#", "C#", "D#"]
    assert _display(notes, "A", "Sharps") == ["A#", "C#", "D#"]
    assert _display(notes, "A", "Flats") == ["Bb", "Db", "Eb"]
    assert [wave_toy.normalize_note_name(note) for note in _display(notes, "A", "Flats")] == notes


def test_harmonic_summary_keeps_internal_sharp_pitch_classes():
    summary = wave_toy.harmonic_summary("Bb", ["Bb", "D", "F"])
    assert summary["root"] == "A#"
    assert summary["selected_notes"] == ["A#", "D", "F"]
    assert summary["selected_display"] == ["Bb", "D", "F"]


def test_note_picker_highlight_set_preserves_selected_pitch_class(qapp):
    picker = wave_toy.CircleOfFifthsNotePicker()
    picker.set_note("C#")
    picker.set_highlight_notes(wave_toy.scale_pitch_classes("A", "major"), "A")
    assert picker.selected_note() == "C#"
    assert "C#" in picker.highlighted_notes()
    assert picker.highlight_root() == "A"


def test_root_change_from_a_to_bb_changes_auto_display_spelling():
    a_notes = wave_toy.scale_pitch_classes("A", "major")
    bb_notes = wave_toy.scale_pitch_classes("Bb", "major")
    assert wave_toy.display_pitch_class_set(a_notes, "A", "Auto") == ["A", "B", "C#", "D", "E", "F#", "G#"]
    assert wave_toy.display_pitch_class_set(bb_notes, "Bb", "Auto") == ["Bb", "C", "D", "Eb", "F", "G", "A"]


def test_a_major_and_minor_scale_highlight_sets_are_pitch_class_stable():
    a_major = set(wave_toy.scale_pitch_classes("A", "major"))
    a_minor = set(wave_toy.scale_pitch_classes("A", "natural_minor"))
    assert {"A", "C#", "E"}.issubset(a_major)
    assert "C" not in a_major
    assert {"A", "C", "E"}.issubset(a_minor)
    assert "C#" not in a_minor


def test_major_triad_chord_tones_are_subset_identifiable_in_scale():
    scale_notes = set(wave_toy.scale_pitch_classes("A", "major"))
    chord_notes = set(wave_toy.chord_pitch_classes("A", "major_triad"))
    assert chord_notes == {"A", "C#", "E"}
    assert chord_notes.issubset(scale_notes)


def test_unknown_scale_and_chord_ids_fall_back_safely():
    assert wave_toy.scale_pitch_classes("A", "missing_scale") == wave_toy.scale_pitch_classes("A", "major")
    assert wave_toy.chord_pitch_classes("A", "missing_chord") == wave_toy.chord_pitch_classes("A", "major_triad")
    assert wave_toy.scale_degree_for_note("C#", "A", "missing_scale") == 3
    assert wave_toy.chord_degree_for_note("E", "A", "missing_chord") == 5


def test_harmony_metadata_export_payload_is_json_safe():
    payload = wave_toy.harmony_metadata_payload("Bb", "major", "major_triad", "Auto", created_at="2026-06-04T00:00:00+00:00")
    assert payload["schema"] == "wavetoy.harmony_metadata.v1"
    assert payload["root_note"] == "A#"
    assert payload["root_display"] == "Bb"
    assert payload["scale_displayed_names"] == ["Bb", "C", "D", "Eb", "F", "G", "A"]
    assert payload["chord_displayed_names"] == ["Bb", "D", "F"]
    assert payload["asset_types_reserved"] == ["scale_pattern", "chord_pattern", "chord_progression"]
    import json

    json.dumps(payload)


def test_harmony_asset_dataclasses_are_json_safe():
    created = "2026-06-04T00:00:00+00:00"
    assets = [
        wave_toy.ScalePatternAsset(uuid="scale-1", name="A Major", created_at=created, modified_at=created),
        wave_toy.ChordPatternAsset(uuid="chord-1", name="A Major Triad", chord_steps=["I"], created_at=created, modified_at=created),
        wave_toy.ChordProgressionAsset(uuid="prog-1", name="I V vi IV", chord_steps=["I", "V", "vi", "IV"], created_at=created, modified_at=created),
    ]
    import json

    for asset in assets:
        data = asset.to_json_dict()
        assert set(data) == {"uuid", "name", "root_note", "spelling_mode", "scale_type", "chord_type", "chord_steps", "tags", "notes", "created_at", "modified_at"}
        json.dumps(data)
