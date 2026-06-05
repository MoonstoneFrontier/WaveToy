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


def test_harmony_json_export_path_appends_json_suffix():
    assert str(wave_toy.harmony_json_export_path("/tmp/wave_toy_harmony")) == "/tmp/wave_toy_harmony.json"
    assert str(wave_toy.harmony_json_export_path("/tmp/wave_toy_harmony.json")) == "/tmp/wave_toy_harmony.json"


def test_harmony_json_import_rejects_wrong_schema():
    import pytest

    with pytest.raises(ValueError):
        wave_toy.harmony_metadata_state_from_payload({"schema": "wrong"})


def test_harmony_json_import_accepts_exported_payload_state():
    payload = wave_toy.harmony_metadata_payload("Bb", "major", "dominant_7", "Auto", created_at="2026-06-04T00:00:00+00:00")
    state = wave_toy.harmony_metadata_state_from_payload(payload)
    assert state == {
        "root_note": "A#",
        "scale_type": "major",
        "chord_root_note": "A#",
        "chord_type": "dominant_7",
        "spelling_mode": "Auto",
    }
    assert wave_toy.display_note_name(state["root_note"], state["root_note"], state["spelling_mode"]) == "Bb"


def _assert_scores_in_range(descriptor):
    assert 0.0 <= descriptor.stability_score <= 1.0
    assert 0.0 <= descriptor.brightness_score <= 1.0
    assert 0.0 <= descriptor.tension_score <= 1.0


def test_scale_descriptor_a_major_notes_and_scores():
    descriptor = wave_toy.scale_descriptor("A", "major")
    assert descriptor.pitch_classes == ["A", "B", "C#", "D", "E", "F#", "G#"]
    assert descriptor.displayed_names == ["A", "B", "C#", "D", "E", "F#", "G#"]
    assert descriptor.degrees == [1, 2, 3, 4, 5, 6, 7]
    assert descriptor.interval_roles[0] == "root"
    _assert_scores_in_range(descriptor)


def test_scale_descriptor_bb_major_auto_displays_flats():
    descriptor = wave_toy.scale_descriptor("Bb", "major", "Auto")
    assert descriptor.pitch_classes == ["A#", "C", "D", "D#", "F", "G", "A"]
    assert descriptor.displayed_names == ["Bb", "C", "D", "Eb", "F", "G", "A"]


def test_chord_descriptor_reports_core_qualities_and_scores():
    assert wave_toy.chord_descriptor("A", "major_triad").chord_quality == "major"
    assert wave_toy.chord_descriptor("A", "minor_triad").chord_quality == "minor"
    diminished = wave_toy.chord_descriptor("B", "diminished_triad")
    assert diminished.chord_quality == "diminished"
    assert diminished.degrees == [1, 3, 5]
    _assert_scores_in_range(diminished)


def test_roman_numerals_for_major_and_minor_keys():
    assert wave_toy.roman_numeral_for_chord("A", "major_triad", "A", "major") == "I"
    assert wave_toy.roman_numeral_for_chord("E", "dominant_7", "A", "major") == "V7"
    assert wave_toy.roman_numeral_for_chord("F#", "minor_triad", "A", "major") == "vi"
    assert wave_toy.roman_numeral_for_chord("C", "major_triad", "A", "natural_minor") == "III"
    assert wave_toy.roman_numeral_for_chord("Bb", "major_triad", "A", "major") in {"chromatic", "non-diatonic"}


def test_chord_descriptor_includes_roman_and_function_relative_to_key():
    descriptor = wave_toy.chord_descriptor("E", "dominant_7", "A", "major")
    assert descriptor.roman_numeral == "V7"
    assert descriptor.harmonic_function == "dominant"
    _assert_scores_in_range(descriptor)


def test_harmony_export_payload_includes_descriptors():
    payload = wave_toy.harmony_metadata_payload("A", "major", "dominant_7", "Auto", chord_root_note="E", created_at="2026-06-04T00:00:00+00:00")
    assert payload["scale_descriptor"]["displayed_names"] == ["A", "B", "C#", "D", "E", "F#", "G#"]
    assert payload["chord_root_note"] == "E"
    assert payload["chord_descriptor"]["roman_numeral"] == "V7"
    assert payload["chord_descriptor"]["harmonic_function"] == "dominant"


def test_music_theory_subtab_labels():
    assert wave_toy.MUSIC_THEORY_SUBTAB_LABELS == (
        "Notes",
        "Intervals",
        "Scales",
        "Chords",
        "Harmony Analysis",
        "Export",
    )


def test_music_theory_sidebar_policy():
    assert wave_toy.music_theory_picker_width_policy() == {
        "minimum": 220,
        "preferred": 300,
        "maximum": 380,
    }


def test_harmony_layout_helpers():
    class FakeSidebar:
        def __init__(self):
            self.minimum_width = None
            self.maximum_width = None
            self.resized_to = None
            self.size_policy = None

        def setMinimumWidth(self, width):
            self.minimum_width = width

        def setMaximumWidth(self, width):
            self.maximum_width = width

        def height(self):
            return 144

        def resize(self, width, height):
            self.resized_to = (width, height)

        def setSizePolicy(self, horizontal, vertical):
            self.size_policy = (horizontal, vertical)

    sidebar = FakeSidebar()
    wave_toy.apply_music_theory_sidebar_width_policy(sidebar)

    assert sidebar.minimum_width == 220
    assert sidebar.maximum_width == 380
    assert sidebar.resized_to == (300, 144)
    assert sidebar.size_policy == (getattr(wave_toy.QSizePolicy, "Preferred", 0), getattr(wave_toy.QSizePolicy, "Expanding", 1))
